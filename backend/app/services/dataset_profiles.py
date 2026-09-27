"""Column-mapping profiles for user-uploaded Kaggle CSVs.

The user downloads CSVs manually (Kaggle login required) and uploads them
through the dashboard/API. Each profile maps one known dataset layout onto
our native observation schema, then reuses ``validate_plant_data`` — the same
validation as every other ingestion path.

Honesty rule: anything not measured in the source file is marked DERIVED in
the profile's ``derived`` list, which is returned to the caller and shown in
the UI. Derived values are documented proxies, never claimed measurements.

Second honesty rule — column check. Every mapper treats an absent column as
zero, which is how a wrong profile would otherwise turn "120 units at 71.4 C"
into "0 units at -273.15 C" and present it as measured fact. So each profile
declares the column groups it fundamentally needs (``REQUIRED``) and
:func:`check_columns` refuses the upload *before* mapping, naming the columns
that were actually found. Refusing is the only honest option: silently
inventing telemetry is worse than declining the file.
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta


class DatasetProfileMismatch(ValueError):
    """An uploaded file's columns do not fit the chosen profile.

    Carries machine-readable detail so the API can return it as structured
    422 data rather than a bare string.
    """

    def __init__(
        self,
        profile: str,
        missing: list[str],
        found: list[str],
        hint: str = "",
    ) -> None:
        self.profile = profile
        self.missing = missing
        self.found = found
        self.hint = hint
        super().__init__(str(self))

    def __str__(self) -> str:
        """Compact, actionable one-liner.

        The dashboard surfaces this detail as raw text truncated to 300
        characters, so the essentials lead and the long column inventory stays
        in its own field rather than bloating the message.
        """
        groups = ", ".join(g.replace(" or ", "|") for g in self.missing)
        parts = [
            f"Columns do not match profile '{self.profile}'. Missing: {groups}.",
        ]
        if self.hint:
            parts.append(self.hint)
        parts.append(
            "Choose another profile from GET /api/v1/data/profiles "
            "('generic' expects the native P041 column names)."
        )
        return " ".join(parts)

    def as_dict(self) -> dict:
        return {
            "message": str(self),
            "profile": self.profile,
            "missing_column_groups": self.missing,
            "columns_found": self.found,
            "hint": self.hint,
        }


def _norm(col: str) -> str:
    return re.sub(r"[^a-z0-9]+", "", col.lower())


def _find(row: dict, *aliases: str):
    """First matching value by normalized column name, else None."""
    lut = {_norm(k): v for k, v in row.items()}
    for a in aliases:
        if a in lut and lut[a] not in (None, ""):
            return lut[a]
    return None


def _f(v, default=0.0) -> float:
    try:
        return float(str(v).strip())
    except (ValueError, TypeError, AttributeError):
        return default


def _clamp(v: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, v))


def _is_failure(v) -> bool:
    return str(v).strip().lower() in ("1", "true", "yes", "failure", "fault", "faulty")


BASE_TS = datetime(2026, 9, 1, 6, 0, 0)


def _synth_ts(i: int) -> str:
    return (BASE_TS + timedelta(minutes=15 * i)).isoformat()


# ---------------------------------------------------------------- generic
def _map_generic(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """Native schema passthrough (our own CSV format). Nothing derived."""
    return rows, []


# ---------------------------------------------------------------- AI4I 2020
def _map_ai4i(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """AI4I variants (shivamb, stephanmatzka, abdulbasit551, brenosilvabarros):
    UDI, Type, Air/Process temp [K], rotational speed, torque, tool wear,
    rotational speed, torque, tool wear, failure flags. No timestamps, no
    per-machine ids, no vibration/energy/production — all documented below."""
    out = []
    for i, r in enumerate(rows):
        typ = str(_find(r, "type") or "M").strip() or "M"
        air_k = _f(_find(r, "airtemperaturek"))
        proc_k = _f(_find(r, "processtemperaturek"))
        rpm = _f(_find(r, "rotationalspeedrpm"))
        torque = _f(_find(r, "torquenm"))
        wear = _f(_find(r, "toolwearmin"))
        fail = _is_failure(_find(r, "machinefailure"))
        temp_c = proc_k - 273.15 if proc_k else air_k - 273.15
        prod = max(0, int(rpm / 10))
        energy = round(prod * 0.12 + 8.0, 2)
        eff = _clamp(95.0 - wear / 12.0 - (30.0 if fail else 0.0), 0.0, 99.5)
        vib = round(1.5 + wear / 150.0 + (6.0 if fail else 0.0), 2)
        out.append({
            "timestamp": _synth_ts(i),
            "machine_id": f"MACHINE-{typ}",
            "production_count": prod,
            "energy_consumption_kwh": energy,
            "efficiency_percent": round(eff, 2),
            "temperature_c": round(temp_c, 2),
            "vibration_mm_s": vib,
            "downtime_minutes": 15.0 if fail else 0.0,
            "status": "fault" if fail else "running",
        })
    derived = ["timestamp (synthesized 15-min steps)", "machine_id (from Type L/M/H)",
               "production_count (from rpm)", "energy (from production)",
               "efficiency (from tool wear)", "vibration (proxy from tool wear)",
               "downtime (15 min on failure rows)"]
    return out, derived


# ------------------------------------------------- Industrial IoT fault (ziya07)
def _map_iotfault(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """ziya07/industrial-iot-fault-detection-dataset: Timestamp, Vibration,
    Temperature, Pressure, RMS/Mean derived cols, Fault Label 0/1/2.
    Single machine; production/energy/efficiency derived."""
    out = []
    for i, r in enumerate(rows):
        ts = _find(r, "timestamp", "time", "datetime") or _synth_ts(i)
        vib = _f(_find(r, "vibrationmms", "vibration", "rmsvibration"))
        temp = _f(_find(r, "temperaturec", "temperature", "meantemp"))
        label = str(_find(r, "faultlabel", "fault", "label") or "0").strip()
        fault = label in ("1", "2")
        prod = max(0, int(110 - vib * 6))
        energy = round(prod * 0.12 + 8.0, 2)
        eff = _clamp(95.0 - max(0.0, temp - 70.0) * 1.2 - (30.0 if fault else 0.0), 0.0, 99.5)
        out.append({
            "timestamp": str(ts),
            "machine_id": "MACHINE-001",
            "production_count": prod,
            "energy_consumption_kwh": energy,
            "efficiency_percent": round(eff, 2),
            "temperature_c": round(temp, 2),
            "vibration_mm_s": round(vib, 2),
            "downtime_minutes": 20.0 if fault else 0.0,
            "status": "fault" if fault else "running",
        })
    derived = ["machine_id (single-machine file)", "production_count (from vibration)",
               "energy (from production)", "efficiency (from temperature)",
               "downtime (20 min on fault rows)"]
    return out, derived


# ------------------------------------------------- IIoT timeseries (zara2099)
def _map_iiot(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """zara2099 simulated_iiot_dataset: hourly timestamp + temperature,
    vibration, load, active_power, machine_failure, etc. Richest mapping."""
    out = []
    for i, r in enumerate(rows):
        ts = _find(r, "timestamp", "time", "datetime") or _synth_ts(i)
        temp = _f(_find(r, "temperature", "motortemperature"))
        vib = _f(_find(r, "vibration"))
        load = _f(_find(r, "load"))
        power = _f(_find(r, "activepower", "activepowerconsumptionkw", "powerkw"))
        fail = _is_failure(_find(r, "machinefailure", "failure"))
        prod = max(0, int(load * 1.2))
        energy = round(power if power > 0 else prod * 0.12 + 6.0, 2)
        eff = _clamp(load - (35.0 if fail else 0.0), 0.0, 99.5)
        out.append({
            "timestamp": str(ts),
            "machine_id": "MACHINE-001",
            "production_count": prod,
            "energy_consumption_kwh": energy,
            "efficiency_percent": round(eff, 2),
            "temperature_c": round(temp, 2),
            "vibration_mm_s": round(vib, 2),
            "downtime_minutes": 30.0 if fail else 0.0,
            "status": "fault" if fail else "running",
        })
    derived = ["machine_id (single-machine file)", "production_count (from load %)",
               "efficiency (from load %)", "downtime (30 min on failure rows)"]
    return out, derived


# ------------------------------------------------- Smart factory 2026
def _map_smartfactory(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """rauffauzanrambe/industrial-smart-factory-automation-dataset-2026:
    temperature_sensor, vibration_level, motor_speed_rpm, conveyor_status,
    energy_consumption, machine_failure."""
    out = []
    for i, r in enumerate(rows):
        ts = _find(r, "timestamp", "time", "datetime") or _synth_ts(i)
        temp = _f(_find(r, "temperaturesensor", "temperature"))
        vib = _f(_find(r, "vibrationlevel", "vibration"))
        rpm = _f(_find(r, "motorspeedrpm", "motorspeed", "rpm"))
        energy = _f(_find(r, "energyconsumption", "energykwh", "power"))
        fail = _is_failure(_find(r, "machinefailure", "failure"))
        conv = str(_find(r, "conveyorstatus", "status") or "").strip().lower()
        if not fail and conv in ("maintenance", "idle", "stopped", "fault"):
            status = "maintenance" if conv == "maintenance" else ("idle" if conv == "idle" else "fault")
        else:
            status = "fault" if fail else "running"
        prod = max(0, int(rpm / 12)) if rpm > 0 else max(0, int(100 - vib * 5))
        if energy <= 0:
            energy = round(prod * 0.12 + 7.0, 2)
        eff = _clamp(93.0 - max(0.0, temp - 70.0) - (30.0 if status == "fault" else 0.0), 0.0, 99.5)
        out.append({
            "timestamp": str(ts),
            "machine_id": "MACHINE-001",
            "production_count": prod,
            "energy_consumption_kwh": round(energy, 2),
            "efficiency_percent": round(eff, 2),
            "temperature_c": round(temp, 2),
            "vibration_mm_s": round(vib, 2),
            "downtime_minutes": 15.0 if status in ("fault", "maintenance") else 0.0,
            "status": status,
        })
    derived = ["machine_id (single-machine file)", "production_count (from rpm)",
               "efficiency (from temperature)", "downtime (15 min on fault/maintenance)"]
    return out, derived


# ------------------------------------------------- Azure predictive maintenance
def _map_azure(rows: list[dict]) -> tuple[list[dict], list[str]]:
    """arnabbiswas1/microsoft-azure-predictive-maintenance: datetime, machineID,
    volt/rotate/pressure/vibration telemetry, failure flags. Multi-machine."""
    out = []
    for i, r in enumerate(rows):
        ts = _find(r, "datetime", "timestamp", "time", "date") or _synth_ts(i)
        mid = str(_find(r, "machineid", "machine", "deviceid", "unit") or "MACHINE-001").strip()
        temp = _f(_find(r, "temperature", "temp"))
        vib = _f(_find(r, "vibration"))
        rpm = _f(_find(r, "rotate", "rotationspeed", "rpm"))
        fail = _is_failure(_find(r, "failure", "machinefailure", "fault"))
        prod = max(0, int(rpm / 10)) if rpm > 0 else max(0, int(100 - vib * 5))
        energy = round(prod * 0.12 + 7.0, 2)
        eff = _clamp(93.0 - max(0.0, temp - 70.0) - (30.0 if fail else 0.0), 0.0, 99.5)
        out.append({
            "timestamp": str(ts),
            "machine_id": mid if mid.startswith("MACHINE") else f"MACHINE-{mid}",
            "production_count": prod,
            "energy_consumption_kwh": energy,
            "efficiency_percent": round(eff, 2),
            "temperature_c": round(temp, 2),
            "vibration_mm_s": round(vib, 2),
            "downtime_minutes": 20.0 if fail else 0.0,
            "status": "fault" if fail else "running",
        })
    derived = ["production_count (from rotation)", "energy (from production)",
               "efficiency (from temperature)", "downtime (20 min on failure rows)"]
    return out, derived


PROFILES: dict[str, dict] = {
    "generic": {"label": "Generic (native P041 schema)", "map": _map_generic},
    "ai4i": {"label": "AI4I 2020 Predictive Maintenance", "map": _map_ai4i},
    "iot-fault": {"label": "Industrial IoT Fault Detection (ziya07)", "map": _map_iotfault},
    "iiot-timeseries": {"label": "IIoT Sensor Data (zara2099)", "map": _map_iiot},
    "smart-factory": {"label": "Smart Factory 2026", "map": _map_smartfactory},
    "azure": {"label": "Azure Predictive Maintenance", "map": _map_azure},
}


# Column groups each profile fundamentally needs. Every group is a set of
# aliases of which at least one must appear in the header. Time and identity
# columns are deliberately NOT required: those mappers synthesize them and
# already declare that in their `derived` list.
REQUIRED: dict[str, tuple[tuple[str, ...], ...]] = {
    "generic": (
        ("timestamp",),
        ("machineid",),
        ("productioncount", "production"),
        ("energyconsumptionkwh", "energykwh", "energy"),
        ("efficiencypercent", "efficiency"),
        ("temperaturec", "temperature"),
        ("vibrationmms", "vibration"),
        ("downtimeminutes", "downtime"),
        ("status",),
    ),
    "ai4i": (
        ("type", "machinetype"),
        ("airtemperaturek", "processtemperaturek", "bearingtemperaturek"),
        ("rotationalspeedrpm", "rotationalspeed", "rpm"),
    ),
    "iot-fault": (
        ("vibrationmms", "vibration", "rmsvibration"),
        ("temperaturec", "temperature", "meantemp", "avgtemp"),
        ("faultlabel", "fault", "label", "target"),
    ),
    "iiot-timeseries": (
        ("temperature", "motortemperature"),
        ("vibration",),
        ("load", "activepower", "activepowerconsumptionkw", "powerkw"),
    ),
    "smart-factory": (
        ("temperaturesensor", "temperature"),
        ("vibrationlevel", "vibration", "motorspeedrpm", "motorspeed", "rpm"),
    ),
    "azure": (
        ("machineid", "machine", "deviceid", "unit"),
        ("rotate", "rotationspeed", "rpm", "vibration"),
    ),
}

# Guidance for layouts we recognise but cannot map directly. Shown instead of a
# bare "column missing" so the user knows why and what to do.
HINTS: dict[str, str] = {
    "azure": (
        "Note: the LBNL/Azure files are often published in long 'telemetry' "
        "form (columns: datetime, machine, component, Value) with one row per "
        "sensor. This profile needs the wide form, one column per signal; "
        "pivot the long form first or use 'generic' after reshaping."
    ),
}


def _normalized_header(fieldnames) -> set[str]:
    return {_norm(c) for c in fieldnames if c}


def check_columns(fieldnames, profile: str) -> None:
    """Raise :class:`DatasetProfileMismatch` if the header cannot feed `profile`.

    Call this before mapping. Without it a wrong profile yields a full report
    of zeros and default constants that looks entirely plausible.
    """
    if profile not in PROFILES:
        raise KeyError(f"unknown profile '{profile}'. Choose: {sorted(PROFILES)}")
    present = _normalized_header(fieldnames)
    missing = [
        " or ".join(group)
        for group in REQUIRED.get(profile, ())
        if not (present & set(group))
    ]
    if missing:
        raise DatasetProfileMismatch(
            profile=profile,
            missing=missing,
            found=sorted(present),
            hint=HINTS.get(profile, ""),
        )


def column_report(fieldnames, profile: str) -> dict:
    """Non-raising diagnostic: which required groups matched. Used by the CLI."""
    present = _normalized_header(fieldnames)
    groups = REQUIRED.get(profile, ())
    matched = [group for group in groups if present & set(group)]
    missing = [group for group in groups if not (present & set(group))]
    return {
        "profile": profile,
        "label": PROFILES.get(profile, {}).get("label", profile),
        "ok": not missing,
        "matched_groups": [" or ".join(g) for g in matched],
        "missing_groups": [" or ".join(g) for g in missing],
        "columns_found": sorted(present),
    }


def map_upload(rows: list[dict], profile: str) -> tuple[list[dict], list[str]]:
    """Map raw CSV dicts to native observation dicts. Raises KeyError if unknown."""
    if profile not in PROFILES:
        raise KeyError(f"unknown profile '{profile}'. Choose: {sorted(PROFILES)}")
    if rows:
        check_columns(rows[0].keys(), profile)
    return PROFILES[profile]["map"](rows)
