from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.analytics import router as analytics_router
from app.api.data import router as data_router
from app.api.reports import router as reports_router
from app.core.dotenv import resolve

app = FastAPI(
    title="Plant Report AI",
    description="Automated Report Generation from Plant Data with LLMs",
    version="0.1.0",
)

# Minimal CORS for the Vite dev server (override via CORS_ORIGINS, comma-separated).
_cors_origins = [
    o.strip()
    for o in resolve("CORS_ORIGINS", "http://localhost:5173").split(",")
    if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Authorization"],
)

app.include_router(data_router)
app.include_router(analytics_router)
app.include_router(reports_router)


@app.get("/health")
def health():
    return {"status": "ok"}
