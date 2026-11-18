"""NotifAI FastAPI service.

Endpoints:
    POST /ingest  - Ingest a notice into the RAG pipeline
    POST /query   - Run the multi-agent workflow on a message
    GET  /health  - Health check
    GET  /metrics - Observability metrics summary
"""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import Depends, FastAPI, HTTPException, Request
from pydantic import BaseModel, Field
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from notifai.agents.router import RouterOutput, route_message
from notifai.api.auth import verify_api_key
from notifai.config.settings import settings
from notifai.observability.tracing import get_metrics_summary, get_recent_traces

logging.basicConfig(level=getattr(logging, settings.log_level, logging.INFO))
logger = logging.getLogger(__name__)

limiter = Limiter(key_func=get_remote_address)

app = FastAPI(
    title="NotifAI Enterprise",
    description="Multi-agent RAG-powered WhatsApp-to-Calendar system",
    version="2.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


# === Request / Response Models ===


class IngestRequest(BaseModel):
    """Request to ingest a notice into the RAG pipeline."""

    text: str = Field(description="Raw notice text", min_length=1, max_length=10000)
    source_chat: str | None = Field(default=None, description="Source chat/group name")
    source_sender: str | None = Field(default=None, description="Sender name")
    metadata: dict[str, Any] | None = Field(default=None, description="Extra metadata")


class IngestResponse(BaseModel):
    """Response from the ingest endpoint."""

    status: str
    chunks_ingested: int = 0
    error: str | None = None


class QueryRequest(BaseModel):
    """Request to query the multi-agent workflow."""

    message: str = Field(description="Message to process", min_length=1, max_length=10000)
    source_chat: str | None = None
    source_sender: str | None = None
    session_id: str | None = None
    dry_run: bool = Field(default=True, description="Don't actually create calendar events")
    enable_rag: bool = Field(default=True, description="Enable RAG retrieval")
    enable_validation: bool = Field(default=True, description="Enable validator agent")
    max_retries: int = Field(default=2, ge=0, le=5)


class QueryResponse(BaseModel):
    """Response from the query endpoint."""

    session_id: str
    events_extracted: int
    events_validated: int
    events_scheduled: int
    retries: int
    errors: list[str]
    cost_usd: float
    latency_ms: float


class HealthResponse(BaseModel):
    """Health check response."""

    status: str
    version: str
    rag_healthy: bool
    calendar_configured: bool
    api_key_required: bool


# === Endpoints ===


@app.post("/ingest", response_model=IngestResponse)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}second")
async def ingest(
    request: Request,
    body: IngestRequest,
    _: Annotated[str, Depends(verify_api_key)],
) -> IngestResponse:
    """Ingest a notice into the RAG pipeline."""
    try:
        from notifai.tools.rag_tool import ingest_notice

        result = ingest_notice(
            text=body.text,
            metadata={
                "source_chat": body.source_chat,
                "source_sender": body.source_sender,
                **(body.metadata or {}),
            },
        )

        if result.get("status") == "error":
            return IngestResponse(
                status="error",
                chunks_ingested=0,
                error=result.get("error", "Unknown error"),
            )

        return IngestResponse(
            status="success",
            chunks_ingested=result.get("chunks_ingested", 0),
        )
    except Exception as e:
        logger.error("Ingest failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/query", response_model=QueryResponse)
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}second")
async def query(
    request: Request,
    body: QueryRequest,
    _: Annotated[str, Depends(verify_api_key)],
) -> QueryResponse:
    """Run the multi-agent workflow on a message."""
    try:
        result: RouterOutput = route_message(
            message=body.message,
            source_chat=body.source_chat,
            source_sender=body.source_sender,
            session_id=body.session_id,
            dry_run=body.dry_run,
            enable_validation=body.enable_validation,
            enable_rag=body.enable_rag,
            max_retries=body.max_retries,
        )

        total_cost = 0.0
        if result.extraction:
            total_cost += result.extraction.cost_usd
        if result.validation:
            total_cost += result.validation.validation_cost_usd

        return QueryResponse(
            session_id=result.session_state.session_id,
            events_extracted=len(result.session_state.extracted_events),
            events_validated=len(result.session_state.validated_events),
            events_scheduled=len(result.session_state.scheduled_events),
            retries=result.session_state.validation_retries,
            errors=result.session_state.errors,
            cost_usd=round(total_cost, 6),
            latency_ms=0.0,
        )
    except Exception as e:
        logger.error("Query failed: %s", e)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health", response_model=HealthResponse)
async def health() -> HealthResponse:
    """Health check endpoint."""
    rag_healthy = False
    try:
        from notifai.tools.rag_tool import health_check

        rag_result = health_check()
        rag_healthy = rag_result.get("status") == "healthy"
    except Exception:
        pass

    calendar_configured = bool(settings.google_calendar_credentials)

    return HealthResponse(
        status="healthy" if rag_healthy else "degraded",
        version="2.0.0",
        rag_healthy=rag_healthy,
        calendar_configured=calendar_configured,
        api_key_required=bool(settings.api_key),
    )


@app.get("/metrics")
@limiter.limit(f"{settings.rate_limit_requests}/{settings.rate_limit_window}second")
async def metrics(
    request: Request,
    _: Annotated[str, Depends(verify_api_key)],
) -> dict[str, Any]:
    """Observability metrics summary."""
    summary = get_metrics_summary()
    traces = get_recent_traces(limit=10)
    return {"summary": summary, "recent_traces": traces}


def start_server() -> None:
    """Start the FastAPI server with uvicorn."""
    import uvicorn

    uvicorn.run(
        "notifai.api.main:app",
        host=settings.api_host,
        port=settings.api_port,
        log_level=settings.log_level.lower(),
    )


if __name__ == "__main__":
    start_server()
