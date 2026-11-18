"""Extractor agent: LLM-based structured event extraction with Pydantic schema."""

from __future__ import annotations

import datetime
import json
import logging
import re
import time
from typing import Any

from pydantic import BaseModel, Field

from notifai.config.settings import settings
from notifai.core.schemas import CollegeEvent, CollegeEventList, NoticeType

logger = logging.getLogger(__name__)


class ExtractionInput(BaseModel):
    """Input for the Extractor agent."""

    message: str = Field(description="Raw chat message or notice text")
    source_chat: str | None = Field(default=None, description="Source chat/group name")
    source_sender: str | None = Field(default=None, description="Sender name")


class ExtractionOutput(BaseModel):
    """Output from the Extractor agent."""

    events: list[CollegeEvent] = Field(default_factory=list)
    model_used: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    cost_usd: float = 0.0
    raw_response: str = ""


_EXTRACTION_PROMPT = """You are NotifAI, an intelligent assistant analyzing college and workplace group chats in India.
Extract all actionable events, task reminders, coordination notices, exams, deadlines, and announcements into structured calendar items.
You understand English, Hindi, and colloquial Hinglish.

Today's anchor date is {today} ({today_iso}).

Rules:
1. ANY task, meeting, or reminder (in English, Hindi, or Hinglish) is IMPORTANT (is_important_notice = True).
2. Date parsing:
   - "today", "aaj", "now", "tonight" -> {today_iso}
   - "tomorrow", "kal", "subah kal" -> calculate tomorrow's date.
   - If no date is given for a task reminder, default to {today_iso}.
3. Time parsing:
   - Convert times (e.g. "11:30 AM", "shaam 5 baje", "10 baje") to 24-hour HH:MM.
   - Default to "10:00" if unspecified.
4. Only classify as is_important_notice = False if the text is pure casual chatter.
5. Create a concise, actionable summary title in English.

Output ONLY a valid JSON object matching this schema:
{{"events": [{{"is_important_notice": true, "title": "Title", "date": "YYYY-MM-DD", "time": "HH:MM", "description": "Context", "notice_type": "event|deadline|meeting|reminder|cancellation|announcement"}}]}}"""


def _build_extraction_prompt(today: str, today_iso: str) -> str:
    return _EXTRACTION_PROMPT.format(today=today, today_iso=today_iso)


def _calculate_cost(tokens_in: int, tokens_out: int) -> float:
    input_cost = (tokens_in / 1_000_000) * settings.gemini_input_cost_per_m
    output_cost = (tokens_out / 1_000_000) * settings.gemini_output_cost_per_m
    return round(input_cost + output_cost, 6)


def extract_events(
    message: str,
    source_chat: str | None = None,
    source_sender: str | None = None,
) -> ExtractionOutput:
    """Extract structured events from a message using Gemini.

    This is the core business logic, independent of ADK.
    """
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=settings.google_api_key)
    today = datetime.date.today().strftime("%A, %B %d, %Y")
    today_iso = datetime.date.today().isoformat()

    prompt = _build_extraction_prompt(today, today_iso)
    full_prompt = f"{prompt}\n\nAnalyze this message:\n\n{message}"

    start_time = time.perf_counter()

    try:
        response = client.models.generate_content(
            model=settings.gemini_model,
            contents=full_prompt,
            config=types.GenerateContentConfig(
                temperature=settings.agent_temperature,
                response_mime_type="application/json",
            ),
        )

        latency_ms = (time.perf_counter() - start_time) * 1000
        raw_text = response.text or "{}"

        tokens_in = 0
        tokens_out = 0
        if response.usage_metadata:
            tokens_in = response.usage_metadata.prompt_token_count or 0
            tokens_out = response.usage_metadata.candidates_token_count or 0

        cost = _calculate_cost(tokens_in, tokens_out)

        try:
            data = json.loads(raw_text)
            events = CollegeEventList.model_validate(data)
            for event in events.events:
                if source_chat:
                    event.source_chat = source_chat
                if source_sender:
                    event.source_sender = source_sender
        except (json.JSONDecodeError, Exception) as e:
            logger.warning("Failed to parse LLM response as JSON: %s", e)
            events = CollegeEventList(events=[])

        return ExtractionOutput(
            events=events.events,
            model_used=settings.gemini_model,
            tokens_in=tokens_in,
            tokens_out=tokens_out,
            latency_ms=round(latency_ms, 2),
            cost_usd=cost,
            raw_response=raw_text[:2000],
        )

    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.error("Gemini extraction failed: %s", e)
        return ExtractionOutput(
            events=[],
            model_used=settings.gemini_model,
            tokens_in=0,
            tokens_out=0,
            latency_ms=round(latency_ms, 2),
            cost_usd=0.0,
            raw_response=f"Error: {str(e)}",
        )


def _extract_with_langchain_fallback(message: str) -> ExtractionOutput:
    """Fallback extraction using LangChain (for environments without google-genai)."""
    from langchain_google_genai import ChatGoogleGenerativeAI
    from langchain_core.prompts import ChatPromptTemplate

    today = datetime.date.today().strftime("%A, %B %d, %Y")
    today_iso = datetime.date.today().isoformat()

    llm = ChatGoogleGenerativeAI(
        model=settings.gemini_model,
        temperature=settings.agent_temperature,
        google_api_key=settings.google_api_key,
    )
    structured_llm = llm.with_structured_output(CollegeEventList)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", _build_extraction_prompt(today, today_iso)),
            ("user", "Analyze this message:\n\n{message}"),
        ]
    )

    chain = prompt | structured_llm
    start_time = time.perf_counter()

    try:
        result = chain.invoke({"message": message})
        latency_ms = (time.perf_counter() - start_time) * 1000

        return ExtractionOutput(
            events=result.events if hasattr(result, "events") else [],
            model_used=settings.gemini_model,
            tokens_in=0,
            tokens_out=0,
            latency_ms=round(latency_ms, 2),
            cost_usd=0.0,
            raw_response="langchain fallback",
        )
    except Exception as e:
        latency_ms = (time.perf_counter() - start_time) * 1000
        logger.error("LangChain fallback extraction failed: %s", e)
        return ExtractionOutput(
            events=[],
            model_used=settings.gemini_model,
            tokens_in=0,
            tokens_out=0,
            latency_ms=round(latency_ms, 2),
            cost_usd=0.0,
            raw_response=f"Error: {str(e)}",
        )