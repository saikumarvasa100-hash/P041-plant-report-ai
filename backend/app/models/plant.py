"""DB-model layer placeholder.

Stage 2 keeps a single Pydantic source of truth in
``app.schemas.plant``. This module re-exports it so future
SQLAlchemy models / persistence code has a stable import path
(``app.models.plant``) without duplicating validation.
"""

from app.schemas.plant import PlantObservation, PlantStatus

__all__ = ["PlantObservation", "PlantStatus"]
