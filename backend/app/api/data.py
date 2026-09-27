"""Sample-data + upload API router (simulator service + user CSV ingestion)."""

import csv
import io

from fastapi import APIRouter, File, HTTPException, Query, UploadFile

from app.schemas.analytics import AnalyticsReport
from app.schemas.plant import PlantObservation
from app.services.analytics import analyze_plant
from app.services.dataset_profiles import (
    PROFILES,
    DatasetProfileMismatch,
    check_columns,
    map_upload,
)
from app.services.ingestion import PlantDataValidationError, validate_plant_data
from app.services.simulator import generate_plant_data

router = APIRouter(prefix="/api/v1/data", tags=["data"])

MAX_UPLOAD_BYTES = 5 * 1024 * 1024


@router.get("/sample", response_model=list[PlantObservation])
def get_sample_data(
    machines: int = Query(2, ge=1, le=10),
    observations: int = Query(5, ge=1, le=200),
    seed: int = Query(42),
) -> list[PlantObservation]:
    """Return a small set of generated observations for testing/demo."""
    return generate_plant_data(
        num_machines=machines,
        observations_per_machine=observations,
        seed=seed,
    )


@router.get("/profiles")
def list_upload_profiles() -> list[dict]:
    """Dataset profiles accepted by the upload endpoint."""
    return [{"id": pid, "label": p["label"]} for pid, p in PROFILES.items()]


@router.post("/upload")
def upload_plant_csv(
    file: UploadFile,
    profile: str = Query("generic", description="Dataset profile id from GET /profiles"),
) -> dict:
    """Ingest a user-uploaded CSV: map columns, validate, analyze.

    Returns the mapped observation count, derived-field notes, and the full
    AnalyticsReport. Never stores the file. Invalid rows → HTTP 422 with
    row/field/reason details.
    """
    if profile not in PROFILES:
        raise HTTPException(
            status_code=422, detail=f"unknown profile '{profile}'. Choose: {sorted(PROFILES)}"
        )
    raw = file.file.read(MAX_UPLOAD_BYTES + 1)
    if len(raw) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail="file exceeds 5 MB limit")
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(status_code=422, detail="file is not valid UTF-8 CSV") from None
    reader = csv.DictReader(io.StringIO(text))
    if not reader.fieldnames:
        raise HTTPException(status_code=422, detail="empty file, no header row")
    rows = list(reader)
    if not rows:
        raise HTTPException(status_code=422, detail="no data rows")
    # Refuse a file whose columns cannot feed the chosen profile. Mapping first
    # would silently turn absent columns into zeros and report them as measured.
    try:
        check_columns(reader.fieldnames, profile)
    except DatasetProfileMismatch as exc:
        raise HTTPException(status_code=422, detail=exc.as_dict()) from exc
    mapped, derived = map_upload(rows, profile)
    try:
        observations = validate_plant_data(mapped)
    except PlantDataValidationError as exc:
        raise HTTPException(
            status_code=422,
            detail={"message": f"{len(exc.errors)} invalid row(s) after mapping",
                    "errors": exc.errors[:20]},
        ) from exc
    report = analyze_plant(observations)
    return {
        "filename": file.filename,
        "profile": profile,
        "csv_rows": len(rows),
        "observation_count": len(observations),
        "derived_fields": derived,
        "observations": [o.model_dump(mode="json") for o in observations],
        "analytics": report.model_dump(mode="json"),
    }
