"""Validator/Critic agent: self-reflection on extracted events."""

from __future__ import annotations

import json
import logging

from pydantic import BaseModel, Field

from notifai.core.schemas import CollegeEvent

logger = logging.getLogger(__name__)


class ValidationInput(BaseModel):
    """Input for the Validator agent."""

    events: list[CollegeEvent] = Field(description="Extracted events to validate")
    original_message: str = Field(description="Original message text")
    retry_count: int = Field(default=0, description="Number of retries so far")


class ValidationOutput(BaseModel):
    """Output from the Validator agent."""

    is_valid: bool = Field(description="Whether all events pass validation")
    issues: list[str] = Field(default_factory=list, description="List of issues found")
    corrected_events: list[CollegeEvent] = Field(
        default_factory=list, description="Corrected events"
    )
    retry_needed: bool = Field(default=False, description="Whether a retry is needed")
    confidence_scores: list[float] = Field(
        default_factory=list, description="Per-event confidence scores"
    )
    validation_cost_usd: float = Field(default=0.0)


_VALIDATION_PROMPT = """You are a validation critic for NotifAI, an event extraction system.
Review the following extracted events against the original message text.

For each event, check:
1. Is the event supported by the source text? (hallucination check)
2. Is the date/time reasonable given the message context?
3. Is the title clear and actionable?
4. Are there any missing events that should have been extracted?
5. Are there any duplicate events?

Original message:
{message}

Extracted events:
{events_json}

Output a JSON object:
{{
  "is_valid": true/false,
  "issues": ["list of issues found"],
  "corrected_events": [list of corrected event objects],
  "retry_needed": true/false,
  "confidence_scores": [0.0-1.0 per event]
}}"""


def _build_validation_prompt(
    message: str, events: list[CollegeEvent]
) -> str:
    events_json = json.dumps(
        [
            {
                "title": e.title,
                "date": e.date,
                "time": e.time,
                "description": e.description,
                "is_important_notice": e.is_important_notice,
            }
            for e in events
        ],
        indent=2,
    )
    return _VALIDATION_PROMPT.format(message=message, events_json=events_json)


def validate_events(
    events: list[CollegeEvent],
    original_message: str,
    retry_count: int = 0,
    max_retries: int = 2,
) -> ValidationOutput:
    """Validate extracted events against the original message.

    This is the core business logic, independent of ADK.
    """
    if not events:
        return ValidationOutput(
            is_valid=True,
            issues=[],
            corrected_events=[],
            retry_needed=False,
        )

    issues: list[str] = []
    corrected_events: list[CollegeEvent] = []
    confidence_scores: list[float] = []

    for event in events:
        event_issues: list[str] = []
        confidence = 1.0

        if not event.title or len(event.title.strip()) < 3:
            event_issues.append(f"Event has empty or too-short title: '{event.title}'")
            confidence -= 0.6

        if not event.date or event.date == "1970-01-01":
            event_issues.append(f"Event '{event.title}' has invalid date")
            confidence -= 0.4

        if not event.time or event.time == "00:00":
            event_issues.append(f"Event '{event.title}' has missing time")
            confidence -= 0.2

        title_lower = event.title.lower()
        desc_lower = event.description.lower()
        combined = f"{title_lower} {desc_lower}"

        if any(
            word in combined
            for word in ["meeting", "submit", "exam", "deadline", "call", "bring"]
        ):
            if not any(
                word in original_message.lower()
                for word in ["meeting", "submit", "exam", "deadline", "call", "bring"]
            ):
                event_issues.append(
                    f"Event '{event.title}' may be hallucinated - "
                    "keywords not in original message"
                )
                confidence -= 0.6

        if len(corrected_events) > 0:
            for prev in corrected_events:
                if (
                    prev.title.lower() == event.title.lower()
                    and prev.date == event.date
                ):
                    event_issues.append(
                        f"Duplicate event detected: '{event.title}'"
                    )
                    confidence -= 0.6
                    break

        if confidence < 0.5:
            issues.extend(event_issues)
            corrected_events.append(event)
        else:
            corrected_events.append(event)

        confidence_scores.append(max(0.0, min(1.0, confidence)))

    is_valid = len(issues) == 0
    retry_needed = (
        not is_valid and retry_count < max_retries
    )

    return ValidationOutput(
        is_valid=is_valid,
        issues=issues,
        corrected_events=corrected_events,
        retry_needed=retry_needed,
        confidence_scores=confidence_scores,
    )


def _validate_with_llm(
    events: list[CollegeEvent],
    original_message: str,
) -> ValidationOutput:
    """LLM-based validation using Gemini (optional enhancement)."""
    from google import genai
    from google.genai import types

    from notifai.config.settings import settings

    client = genai.Client(api_key=settings.google_api_key)
    prompt = _build_validation_prompt(original_message, events)

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=prompt,
            config=types.GenerateContentConfig(
                temperature=0.0,
                response_mime_type="application/json",
            ),
        )

        raw_text = response.text or "{}"
        tokens_in = 0
        tokens_out = 0
        if response.usage_metadata:
            tokens_in = response.usage_metadata.prompt_token_count or 0
            tokens_out = response.usage_metadata.candidates_token_count or 0

        cost = round(
            (tokens_in / 1_000_000) * settings.gemini_input_cost_per_m
            + (tokens_out / 1_000_000) * settings.gemini_output_cost_per_m,
            6,
        )

        data = json.loads(raw_text)
        corrected = [
            CollegeEvent.model_validate(e)
            for e in data.get("corrected_events", [])
        ]

        return ValidationOutput(
            is_valid=data.get("is_valid", True),
            issues=data.get("issues", []),
            corrected_events=corrected,
            retry_needed=data.get("retry_needed", False),
            confidence_scores=data.get("confidence_scores", [1.0] * len(events)),
            validation_cost_usd=cost,
        )
    except Exception as e:
        logger.warning("LLM validation failed, falling back to rule-based: %s", e)
        return validate_events(events, original_message)
