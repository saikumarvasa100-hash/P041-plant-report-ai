"""Upload endpoint tests: dataset profiles + CSV ingestion API. Offline."""

import io

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

AI4I_CSV = """UDI,Product ID,Type,Air temperature [K],Process temperature [K],Rotational speed [rpm],Torque [Nm],Tool wear [min],Machine failure,TWF,HDF,PWF,OSF,RNF
1,M1234,L,298.1,308.6,1551,42.8,0,0,0,0,0,0,0
2,M1235,M,298.2,308.7,1408,46.3,3,0,0,0,0,0,0
3,M1236,H,298.3,308.8,1500,40.0,200,1,0,0,0,0,1
"""

AZURE_CSV = """datetime,machineID,volt,rotate,pressure,vibration,failure
2026-09-01 06:00:00,M1,170.0,450.0,100.0,2.0,No Failure
2026-09-01 07:00:00,M1,172.0,455.0,101.0,9.5,Failure
2026-09-01 06:00:00,M2,169.0,448.0,99.0,1.8,No Failure
"""

NATIVE_CSV = """timestamp,machine_id,production_count,energy_consumption_kwh,efficiency_percent,temperature_c,vibration_mm_s,downtime_minutes,status
2026-09-01T06:00:00,MACHINE-001,100,20.0,85.0,65.0,2.0,0.0,running
2026-09-01T06:15:00,MACHINE-001,0,3.0,0.0,45.0,0.5,15.0,maintenance
"""


def _upload(csv_text: str, profile: str, filename: str = "data.csv"):
    return client.post(
        f"/api/v1/data/upload?profile={profile}",
        files={"file": (filename, io.BytesIO(csv_text.encode()), "text/csv")},
    )


def test_profiles_listed():
    ids = {p["id"] for p in client.get("/api/v1/data/profiles").json()}
    assert {"generic", "ai4i", "iot-fault", "iiot-timeseries", "smart-factory", "azure"} <= ids


def test_upload_ai4i():
    resp = _upload(AI4I_CSV, "ai4i")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["observation_count"] == 3
    assert body["analytics"]["plant"]["fault_count"] == 1
    assert any("Derived" in d or "derived" in d.lower() or "synth" in d.lower() or "rpm" in d.lower()
               for d in body["derived_fields"])
    machines = {m["machine_id"] for m in body["analytics"]["machines"]}
    assert machines == {"MACHINE-L", "MACHINE-M", "MACHINE-H"}


def test_upload_azure_multimachine():
    resp = _upload(AZURE_CSV, "azure")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["analytics"]["plant"]["machine_count"] == 2
    assert body["analytics"]["plant"]["fault_count"] == 1


def test_upload_generic_native():
    resp = _upload(NATIVE_CSV, "generic")
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["observation_count"] == 2
    assert body["derived_fields"] == []


def test_upload_unknown_profile():
    assert _upload(NATIVE_CSV, "nope").status_code == 422


def test_upload_empty_file():
    resp = client.post(
        "/api/v1/data/upload?profile=generic",
        files={"file": ("e.csv", io.BytesIO(b""), "text/csv")},
    )
    assert resp.status_code == 422


def test_upload_garbage_csv_rejected():
    resp = _upload("not,a,real\n1,2\n", "generic")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    # Either the row-level validator or the column check may reject first.
    if isinstance(detail, dict):
        assert detail["message"]
    else:
        assert "errors" in detail or "invalid" in detail.lower()


# ---------------- column/profile mismatch guard ----------------


def test_wrong_profile_is_refused_not_zero_filled():
    """A native CSV under the ai4i profile must be refused, not mapped to zeros.

    Without the column check this produced production 0, efficiency 95% and
    temperature -273.15 C from a row that really said 120 units at 71.4 C.
    """
    resp = _upload(NATIVE_CSV, "ai4i")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert detail["profile"] == "ai4i"
    assert detail["missing_column_groups"]
    assert "rotationalspeedrpm" in detail["message"]


def test_mismatch_detail_lists_columns_found():
    resp = _upload(NATIVE_CSV, "iot-fault")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    # The inventory of what the file actually has lives in its own field so the
    # message stays short enough to survive the dashboard's 300-char truncation.
    found = detail["columns_found"]
    assert "machineid" in found
    assert "productioncount" in found
    assert "Columns found" not in detail["message"]


def test_mismatch_message_survives_dashboard_truncation():
    """The dashboard shows resp.text().slice(0, 300); the fix must fit in that."""
    resp = _upload(NATIVE_CSV, "ai4i")
    detail = resp.json()["detail"]
    assert len(detail["message"]) <= 300
    # The two things a user needs must be inside the truncated window.
    shown = detail["message"][:300]
    assert "ai4i" in shown
    assert "rotationalspeedrpm" in shown
    assert "/profiles" in shown


def test_each_profile_accepts_its_own_headers():
    """Every profile must accept a realistic header + row for its own dataset.

    Values are physically plausible on purpose: an all-1s row means 1 K, which
    the validator correctly rejects as -272 C, which would test nothing about
    the column check.
    """
    cases = {
        "ai4i": (
            "UDI,Type,Air temperature [K],Process temperature [K],Rotational speed [rpm],"
            "Torque [Nm],Tool wear [min],Machine failure",
            "1,L,295.3,310.5,1500,40.0,10,0",
        ),
        "iot-fault": (
            "Timestamp,Vibration,Temperature,Fault Label",
            "2026-09-01 06:00:00,2.4,68.5,0",
        ),
        "iiot-timeseries": (
            "timestamp,temperature,vibration,load,active_power,machine_failure",
            "2026-09-01 06:00:00,66.2,2.1,88.0,12.4,0",
        ),
        "smart-factory": (
            "timestamp,temperature_sensor,vibration_level,motor_speed_rpm,"
            "energy_consumption,conveyor_status",
            "2026-09-01 06:00:00,64.8,2.2,1450,18.6,running",
        ),
        "azure": (
            "datetime,machineID,rotate,vibration,failure",
            "2026-09-01 06:00:00,1,1520,2.3,0",
        ),
    }
    for profile, (header, row) in cases.items():
        resp = _upload(f"{header}\n{row}\n", profile)
        assert resp.status_code == 200, f"{profile}: {resp.status_code} {resp.text[:300]}"
        assert resp.json()["observation_count"] >= 1
        # Every non-generic profile must declare what it had to invent.
        if profile != "generic":
            assert resp.json()["derived_fields"], f"{profile} derived nothing"


def test_azure_long_format_gives_actionable_hint():
    """The published LBNL long/telemetry layout cannot be mapped directly.

    It must be refused with an explanation, not silently zero-filled.
    """
    long_csv = "datetime,machine,component,Value\n2026-09-01 06:00:00,1,voltage,420\n"
    resp = _upload(long_csv, "azure")
    assert resp.status_code == 422
    detail = resp.json()["detail"]
    assert "pivot" in detail["hint"].lower()
    assert "telemetry" in detail["hint"].lower()
