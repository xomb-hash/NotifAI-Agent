"""Router/coordinator agent: delegates to sub-agents in sequence."""

from __future__ import annotations

import logging
import uuid

from pydantic import BaseModel, Field

from notifai.agents.extractor import ExtractionInput, ExtractionOutput, extract_events
from notifai.agents.retriever import RetrieverOutput, retrieve_context
from notifai.agents.scheduler import SchedulerOutput, schedule_validated_events
from notifai.agents.validator import ValidationOutput, validate_events
from notifai.core.schemas import CollegeEvent, SessionState
from notifai.observability.tracing import (
    end_trace,
    record_agent_call,
    start_trace,
)

logger = logging.getLogger(__name__)


class RouterInput(BaseModel):
    """Input for the Router agent."""

    message: str = Field(description="Raw chat message or notice text")
    source_chat: str | None = Field(default=None)
    source_sender: str | None = Field(default=None)
    session_id: str | None = Field(default=None)


class RouterOutput(BaseModel):
    """Output from the Router agent."""

    session_state: SessionState = Field(default_factory=SessionState)
    extraction: ExtractionOutput | None = None
    validation: ValidationOutput | None = None
    scheduling: SchedulerOutput | None = None
    retrieval: RetrieverOutput | None = None
    final_events: list[CollegeEvent] = Field(default_factory=list)


def route_message(
    message: str,
    source_chat: str | None = None,
    source_sender: str | None = None,
    session_id: str | None = None,
    dry_run: bool = False,
    enable_validation: bool = True,
    enable_rag: bool = True,
    max_retries: int = 2,
) -> RouterOutput:
    """Route a message through the multi-agent workflow.

    1. Retrieve context (if RAG enabled)
    2. Extract events (Extractor agent)
    3. Validate events (Validator agent) with retry loop
    4. Schedule events (Scheduler agent)

    All steps are traced via the observability module.
    """
    import time

    trace = start_trace(
        request_id=str(uuid.uuid4()),
        session_id=session_id or str(uuid.uuid4()),
    )

    state = SessionState(session_id=session_id or str(uuid.uuid4()))
    state.update_step("router")

    retrieval_output: RetrieverOutput | None = None
    if enable_rag:
        state.update_step("retriever")
        t0 = time.perf_counter()
        try:
            retrieval_output = retrieve_context(
                query=message,
                top_k=3,
                metadata_filter=(
                    {"source_chat": source_chat} if source_chat else None
                ),
            )
            record_agent_call("retriever", (time.perf_counter() - t0) * 1000)
        except Exception as e:
            record_agent_call("retriever", (time.perf_counter() - t0) * 1000, success=False, error=str(e))
            logger.warning("RAG retrieval failed, continuing: %s", e)
            state.add_error(f"RAG retrieval: {e}")

    state.update_step("extractor")
    t0 = time.perf_counter()
    extraction_input = ExtractionInput(
        message=message,
        source_chat=source_chat,
        source_sender=source_sender,
    )
    extraction_output = extract_events(
        message=extraction_input.message,
        source_chat=extraction_input.source_chat,
        source_sender=extraction_input.source_sender,
    )
    state.extracted_events = extraction_output.events
    trace.events_extracted = len(extraction_output.events)
    record_agent_call(
        "extractor",
        (time.perf_counter() - t0) * 1000,
        tokens_in=extraction_output.tokens_in,
        tokens_out=extraction_output.tokens_out,
        cost_usd=extraction_output.cost_usd,
    )

    if not extraction_output.events:
        logger.info("No events extracted from message")
        state.update_step("done")
        result = RouterOutput(
            session_state=state,
            extraction=extraction_output,
            retrieval=retrieval_output,
            final_events=[],
        )
        end_trace()
        return result

    validation_output: ValidationOutput | None = None
    if enable_validation:
        state.update_step("validator")
        retry_count = 0
        current_events = extraction_output.events

        while retry_count <= max_retries:
            t0 = time.perf_counter()
            validation_output = validate_events(
                events=current_events,
                original_message=message,
                retry_count=retry_count,
                max_retries=max_retries,
            )
            record_agent_call(
                "validator",
                (time.perf_counter() - t0) * 1000,
                cost_usd=validation_output.validation_cost_usd,
                success=validation_output.is_valid,
                error="; ".join(validation_output.issues) if validation_output.issues else "",
            )

            if validation_output.is_valid:
                break

            if validation_output.retry_needed:
                retry_count += 1
                state.validation_retries = retry_count
                trace.retries = retry_count
                trace.validation_failures += 1
                logger.info(
                    "Validation retry %d/%d: %s",
                    retry_count,
                    max_retries,
                    "; ".join(validation_output.issues),
                )
                state.update_step("extractor")
                t0 = time.perf_counter()
                extraction_output = extract_events(
                    message=message,
                    source_chat=source_chat,
                    source_sender=source_sender,
                )
                record_agent_call(
                    "extractor_retry",
                    (time.perf_counter() - t0) * 1000,
                    tokens_in=extraction_output.tokens_in,
                    tokens_out=extraction_output.tokens_out,
                    cost_usd=extraction_output.cost_usd,
                )
                current_events = extraction_output.events
                state.extracted_events = current_events
            else:
                break

        state.validated_events = validation_output.corrected_events
    else:
        state.validated_events = extraction_output.events

    if not state.validated_events:
        logger.info("No validated events to schedule")
        state.update_step("done")
        result = RouterOutput(
            session_state=state,
            extraction=extraction_output,
            validation=validation_output,
            retrieval=retrieval_output,
            final_events=[],
        )
        end_trace()
        return result

    state.update_step("scheduler")
    t0 = time.perf_counter()
    scheduling_output = schedule_validated_events(
        events=state.validated_events,
        dry_run=dry_run,
    )
    trace.events_scheduled = scheduling_output.scheduled_count
    record_agent_call(
        "scheduler",
        (time.perf_counter() - t0) * 1000,
        success=scheduling_output.scheduled_count > 0 or dry_run,
        error="; ".join(scheduling_output.errors) if scheduling_output.errors else "",
    )
    state.scheduled_events = state.validated_events

    if enable_rag:
        state.update_step("retriever_ingest")
        t0 = time.perf_counter()
        try:
            from notifai.tools.rag_tool import ingest_notice
            ingest_notice(
                text=message,
                metadata={
                    "source_chat": source_chat,
                    "source_sender": source_sender,
                },
            )
            record_agent_call("rag_ingest", (time.perf_counter() - t0) * 1000)
        except Exception as e:
            record_agent_call("rag_ingest", (time.perf_counter() - t0) * 1000, success=False, error=str(e))
            logger.warning("RAG ingest failed: %s", e)

    state.update_step("done")
    end_trace()

    return RouterOutput(
        session_state=state,
        extraction=extraction_output,
        validation=validation_output,
        scheduling=scheduling_output,
        retrieval=retrieval_output,
        final_events=state.validated_events,
    )
