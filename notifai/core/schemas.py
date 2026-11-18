from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator


class EventStatus(str, Enum):  # noqa: UP042
    PENDING = "pending"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    UPDATED = "updated"


class NoticeType(str, Enum):  # noqa: UP042
    EVENT = "event"
    DEADLINE = "deadline"
    MEETING = "meeting"
    REMINDER = "reminder"
    CANCELLATION = "cancellation"
    ANNOUNCEMENT = "announcement"
    OTHER = "other"


class CollegeEvent(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    is_important_notice: bool = Field(description="True for actionable reminders, events, deadlines")
    title: str = Field(description="Actionable title for the event or reminder")
    date: str = Field(description="Target date in YYYY-MM-DD")
    time: str = Field(description="24-hour time HH:MM format")
    description: str = Field(description="Original message text and location")
    notice_type: NoticeType = Field(default=NoticeType.EVENT)
    status: EventStatus = Field(default=EventStatus.PENDING)
    source_message_id: str | None = None
    source_chat: str | None = None
    source_sender: str | None = None
    source_timestamp: datetime | None = None
    calendar_event_id: str | None = None
    confidence: float = Field(default=1.0, ge=0.0, le=1.0)
    extracted_at: datetime = Field(default_factory=datetime.utcnow)

    @field_validator("date")
    @classmethod
    def validate_date(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%Y-%m-%d")
        except ValueError:
            raise ValueError("Date must be in YYYY-MM-DD format")
        return v

    @field_validator("time")
    @classmethod
    def validate_time(cls, v: str) -> str:
        try:
            datetime.strptime(v, "%H:%M")
        except ValueError:
            raise ValueError("Time must be in HH:MM 24-hour format")
        return v


class CollegeEventList(BaseModel):
    events: list[CollegeEvent] = Field(default_factory=list)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    embedding: list[float] | None = None


class RetrievalResult(BaseModel):
    chunk: Chunk
    score: float


class ExtractionResult(BaseModel):
    events: list[CollegeEvent]
    raw_response: str
    model_used: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float


class ValidationResult(BaseModel):
    is_valid: bool
    issues: list[str] = Field(default_factory=list)
    corrected_events: list[CollegeEvent] = Field(default_factory=list)
    retry_needed: bool = False


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: str | None = None
    chat_id: str | None = None
    message_id: str | None = None
    current_step: str = "router"
    extracted_events: list[CollegeEvent] = Field(default_factory=list)
    validated_events: list[CollegeEvent] = Field(default_factory=list)
    scheduled_events: list[CollegeEvent] = Field(default_factory=list)
    retrieved_context: list[RetrievalResult] = Field(default_factory=list)
    validation_retries: int = 0
    max_validation_retries: int = 2
    errors: list[str] = Field(default_factory=list)
    metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_step(self, step: str) -> None:
        self.current_step = step
        self.updated_at = datetime.utcnow()

    def add_error(self, error: str) -> None:
        self.errors.append(f"{datetime.utcnow().isoformat()}: {error}")
        self.updated_at = datetime.utcnow()
