"""ADK 2.14 multi-agent workflow definition.

This module defines the ADK-compatible agent hierarchy. It uses conditional
imports so the business logic in agents/ can be tested without ADK installed.

Architecture:
    Coordinator (Router)
    ├── Retriever (RAG tool)
    ├── Extractor (Gemini + Pydantic)
    ├── Validator/Critic (self-reflection, max 2 retries)
    └── Scheduler (Google Calendar tool)
"""

from __future__ import annotations

import logging
from typing import Any

from notifai.agents.extractor import extract_events
from notifai.agents.retriever import retrieve_context
from notifai.agents.scheduler import schedule_validated_events
from notifai.agents.validator import validate_events
from notifai.config.settings import settings
from notifai.core.schemas import CollegeEvent

logger = logging.getLogger(__name__)


def _try_import_adk() -> Any:
    try:
        from google.adk.agents.llm_agent import Agent
        return Agent
    except ImportError:
        logger.warning(
            "google-adk not installed. ADK workflow disabled. "
            "Install with: pip install google-adk>=2.14.1"
        )
        return None


def _extractor_tool(
    message: str,
    source_chat: str = "",
    source_sender: str = "",
) -> dict[str, Any]:
    """ADK tool: Extract structured events from a message."""
    result = extract_events(
        message=message,
        source_chat=source_chat or None,
        source_sender=source_sender or None,
    )
    return {
        "events": [e.model_dump() for e in result.events],
        "model_used": result.model_used,
        "tokens_in": result.tokens_in,
        "tokens_out": result.tokens_out,
        "latency_ms": result.latency_ms,
        "cost_usd": result.cost_usd,
    }


def _validator_tool(
    events_json: str,
    original_message: str,
    retry_count: int = 0,
) -> dict[str, Any]:
    """ADK tool: Validate extracted events."""
    import json
    events_data = json.loads(events_json) if isinstance(events_json, str) else events_json
    events = [CollegeEvent.model_validate(e) for e in events_data]
    result = validate_events(
        events=events,
        original_message=original_message,
        retry_count=retry_count,
        max_retries=settings.max_validation_retries,
    )
    return {
        "is_valid": result.is_valid,
        "issues": result.issues,
        "corrected_events": [e.model_dump() for e in result.corrected_events],
        "retry_needed": result.retry_needed,
        "confidence_scores": result.confidence_scores,
        "validation_cost_usd": result.validation_cost_usd,
    }


def _scheduler_tool(
    events_json: str,
    dry_run: bool = False,
) -> dict[str, Any]:
    """ADK tool: Schedule validated events on Google Calendar."""
    import json
    events_data = json.loads(events_json) if isinstance(events_json, str) else events_json
    events = [CollegeEvent.model_validate(e) for e in events_data]
    result = schedule_validated_events(events=events, dry_run=dry_run)
    return {
        "scheduled_count": result.scheduled_count,
        "results": result.results,
        "errors": result.errors,
    }


def _retriever_tool(
    query: str,
    top_k: int = 5,
    metadata_filter_json: str = "",
) -> dict[str, Any]:
    """ADK tool: Retrieve relevant context from RAG."""
    import json
    metadata_filter = json.loads(metadata_filter_json) if metadata_filter_json else None
    result = retrieve_context(query=query, top_k=top_k, metadata_filter=metadata_filter)
    return {
        "results": result.results,
        "deadlines": result.deadlines,
    }


def create_workflow() -> Any:
    """Create the ADK multi-agent workflow.

    Returns the root coordinator agent, or None if ADK is not available.
    """
    Agent = _try_import_adk()
    if Agent is None:
        return None

    from google.adk.agents.llm_agent import Agent

    extractor_agent = Agent(
        name="extractor",
        model=settings.gemini_model,
        description="Extracts structured calendar events from chat messages",
        instruction=(
            "Extract all actionable events, deadlines, meetings, and reminders "
            "from the message. Output structured data with title, date (YYYY-MM-DD), "
            "time (HH:MM), description, and notice_type."
        ),
        tools=[_extractor_tool],
    )

    validator_agent = Agent(
        name="validator",
        model=settings.gemini_model,
        description="Validates extracted events for accuracy and completeness",
        instruction=(
            "Review extracted events against the original message. Check for "
            "hallucinations, missing events, duplicates, and invalid dates/times. "
            "Set retry_needed to true if critical issues are found."
        ),
        tools=[_validator_tool],
    )

    retriever_agent = Agent(
        name="retriever",
        model=settings.gemini_model,
        description="Retrieves relevant context from the RAG pipeline",
        instruction=(
            "Search the notice database for relevant context. Use metadata filters "
            "for source chat, date ranges, and event types."
        ),
        tools=[_retriever_tool],
    )

    scheduler_agent = Agent(
        name="scheduler",
        model=settings.gemini_model,
        description="Schedules validated events on Google Calendar",
        instruction=(
            "Schedule the validated events on Google Calendar. Use dry_run mode "
            "for testing. Report success/failure for each event."
        ),
        tools=[_scheduler_tool],
    )

    coordinator_agent = Agent(
        name="coordinator",
        model=settings.gemini_model,
        description="Routes messages to the appropriate sub-agents",
        instruction=(
            "You are the coordinator of the NotifAI multi-agent system. "
            "Process incoming messages through this pipeline:\n"
            "1. Use the retriever to find relevant context\n"
            "2. Use the extractor to identify calendar events\n"
            "3. Use the validator to check extraction quality (retry up to 2 times)\n"
            "4. Use the scheduler to create calendar events\n\n"
            "Delegate to sub-agents as needed. Report the final result."
        ),
        sub_agents=[extractor_agent, validator_agent, retriever_agent, scheduler_agent],
    )

    return coordinator_agent
