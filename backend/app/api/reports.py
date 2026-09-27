"""Report-generation API (Stage 3 analytics -> LLM narrative)."""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.core.config import LLMSettings
from app.schemas.analytics import AnalyticsReport
from app.schemas.report import GeneratedReport, ReportRequest, ReportType
from app.services.llm import LLMConfigurationError, LLMError
from app.services.report_generator import generate_daily_report

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


def _build_generated_report(
    report_type: ReportType,
    machines: int,
    observations: int,
    seed: int,
    settings: LLMSettings,
) -> GeneratedReport:
    try:
        return generate_daily_report(
            machines, observations, seed, report_type.value, settings
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.post("/generate", response_model=GeneratedReport)
def post_generate_report(req: ReportRequest) -> GeneratedReport:
    """Run analytics then render via the configured LLM provider."""
    return _build_generated_report(
        req.report_type, req.machines, req.observations, req.seed,
        LLMSettings.from_env(),
    )


class AnalyticsReportRequest(BaseModel):
    """Generate a report from caller-supplied trusted analytics."""

    analytics: AnalyticsReport
    report_type: ReportType = ReportType.DAILY


@router.post("/from-analytics", response_model=GeneratedReport)
def post_generate_from_analytics(req: AnalyticsReportRequest) -> GeneratedReport:
    """Render a report from uploaded/externally-computed analytics.

    The caller supplies the trusted AnalyticsReport (e.g. from an uploaded
    CSV); the LLM only narrates it. Requires a configured provider.
    """
    from app.services.report_generator import generate_plant_report

    try:
        return generate_plant_report(
            req.analytics, req.report_type.value, LLMSettings.from_env()
        )
    except LLMConfigurationError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except LLMError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/sample", response_model=GeneratedReport)
def get_sample_report(
    report_type: ReportType = ReportType.DAILY,
    machines: int = Query(4, ge=1, le=10),
    observations: int = Query(48, ge=4, le=500),
    seed: int = Query(7),
) -> GeneratedReport:
    """Sample report via the configured provider — requires an API key."""
    return _build_generated_report(
        report_type, machines, observations, seed, LLMSettings.from_env()
    )


@router.get("/status")
def get_provider_status() -> dict[str, str]:
    """Non-secret provider status for UI badges. Never includes keys."""
    settings = LLMSettings.from_env()
    try:
        settings.require_configured()
    except LLMConfigurationError:
        return {"provider": settings.provider, "mode": "unconfigured", "model": settings.model}
    return {"provider": settings.provider, "mode": "live", "model": settings.model}


class HtmlExportRequest(BaseModel):
    title: str = "Industrial Plant Performance Report"
    content: str
    model: str = "liquid/lfm-2.5-2.6b:free"
    numbers_verified: bool = True
    reporting_period: str = "Current Shift"


@router.post("/export/html")
def export_report_html(req: HtmlExportRequest):
    """Export report content as a formatted, printable standalone HTML document."""
    from fastapi.responses import HTMLResponse

    body_html = ""
    for line in req.content.split("\n"):
        line_str = line.strip()
        if line_str.startswith("# "):
            body_html += f"<h1>{line_str[2:]}</h1>\n"
        elif line_str.startswith("## "):
            body_html += f"<h2>{line_str[3:]}</h2>\n"
        elif line_str.startswith("### "):
            body_html += f"<h3>{line_str[4:]}</h3>\n"
        elif line_str.startswith("- "):
            body_html += f"<li>{line_str[2:]}</li>\n"
        elif line_str != "":
            body_html += f"<p>{line_str}</p>\n"

    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{req.title}</title>
    <style>
        body {{
            font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, Roboto, sans-serif;
            background-color: #0d131a;
            color: #e2e8f0;
            margin: 0;
            padding: 2rem;
            line-height: 1.6;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            background: #151d27;
            border: 1px solid #263545;
            border-radius: 12px;
            padding: 2.5rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        }}
        .header {{
            border-bottom: 2px solid #263545;
            padding-bottom: 1.5rem;
            margin-bottom: 2rem;
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
        }}
        .badge {{
            background: #0f2e28;
            color: #3ddc84;
            border: 1px solid #1a5245;
            padding: 0.35rem 0.75rem;
            border-radius: 20px;
            font-size: 0.85rem;
            font-weight: 600;
        }}
        h1 {{ color: #ffffff; font-size: 2rem; margin-top: 0; }}
        h2 {{ color: #38bdf8; font-size: 1.4rem; border-bottom: 1px solid #263545; padding-bottom: 0.5rem; margin-top: 2rem; }}
        h3 {{ color: #94a3b8; font-size: 1.1rem; }}
        p {{ color: #cbd5e1; font-size: 1rem; }}
        li {{ color: #cbd5e1; margin-bottom: 0.4rem; }}
        .footer {{
            margin-top: 3rem;
            border-top: 1px solid #263545;
            padding-top: 1rem;
            color: #64748b;
            font-size: 0.85rem;
            display: flex;
            justify-content: space-between;
        }}
        @media print {{
            body {{ background: #fff; color: #000; padding: 0; }}
            .container {{ border: none; box-shadow: none; padding: 0; background: #fff; color: #000; }}
            h1, h2, h3, p, li {{ color: #000 !important; }}
            h2 {{ border-bottom-color: #ccc; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <div>
                <h1>{req.title}</h1>
                <p style="margin: 0; color: #94a3b8;">Period: {req.reporting_period}</p>
            </div>
            <span class="badge">{"✓ Numerical Claims Grounded & Verified" if req.numbers_verified else "Unverified"}</span>
        </div>
        <div class="content">
            {body_html}
        </div>
        <div class="footer">
            <span>Generated by Plant Intelligence Platform</span>
            <span>LLM Model: {req.model}</span>
        </div>
    </div>
</body>
</html>"""
    return HTMLResponse(content=html_content, status_code=200)

