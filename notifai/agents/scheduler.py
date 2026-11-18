"""Scheduler agent: schedules validated events on Google Calendar."""

from __future__ import annotations

import logging
from typing import Any

from pydantic import BaseModel, Field

from notifai.core.schemas import CollegeEvent
from notifai.tools.calendar_tool import schedule_event

logger = logging.getLogger(__name__)


class SchedulerInput(BaseModel):
    """Input for the Scheduler agent."""

    events: list[CollegeEvent] = Field(description="Validated events to schedule")
    dry_run: bool = Field(
        default=False, description="If True, don't actually create calendar events"
    )


class SchedulerOutput(BaseModel):
    """Output from the Scheduler agent."""

    scheduled_count: int = Field(default=0)
    results: list[dict[str, Any]] = Field(default_factory=list)
    errors: list[str] = Field(default_factory=list)


def schedule_validated_events(
    events: list[CollegeEvent],
    dry_run: bool = False,
) -> SchedulerOutput:
    """Schedule validated events on Google Calendar.

    This is the core business logic, independent of ADK.
    """
    if not events:
        return SchedulerOutput(scheduled_count=0, results=[], errors=[])

    if dry_run:
        logger.info("Dry run: would schedule %d events", len(events))
        return SchedulerOutput(
            scheduled_count=0,
            results=[
                {"status": "dry_run", "title": e.title, "date": e.date, "time": e.time}
                for e in events
            ],
            errors=[],
        )

    results: list[dict[str, Any]] = []
    errors: list[str] = []
    scheduled_count = 0

    for event in events:
        result = schedule_event(event)
        results.append(result)
        if result.get("status") == "scheduled":
            scheduled_count += 1
        else:
            errors.append(f"Failed to schedule '{event.title}': {result.get('error')}")

    logger.info(
        "Scheduled %d/%d events successfully", scheduled_count, len(events)
    )

    return SchedulerOutput(
        scheduled_count=scheduled_count,
        results=results,
        errors=errors,
    )
