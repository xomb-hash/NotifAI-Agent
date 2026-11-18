from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Literal, Dict, Any
from datetime import datetime
from enum import Enum
import uuid


class EventStatus(str, Enum):
    PENDING = "pending"
    SCHEDULED = "scheduled"
    CANCELLED = "cancelled"
    UPDATED = "updated"


class NoticeType(str, Enum):
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
    source_message_id: Optional[str] = None
    source_chat: Optional[str] = None
    source_sender: Optional[str] = None
    source_timestamp: Optional[datetime] = None
    calendar_event_id: Optional[str] = None
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
    events: List[CollegeEvent] = Field(default_factory=list)


class Chunk(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    content: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    embedding: Optional[List[float]] = None


class RetrievalResult(BaseModel):
    chunk: Chunk
    score: float


class ExtractionResult(BaseModel):
    events: List[CollegeEvent]
    raw_response: str
    model_used: str
    tokens_in: int
    tokens_out: int
    latency_ms: float
    cost_usd: float


class ValidationResult(BaseModel):
    is_valid: bool
    issues: List[str] = Field(default_factory=list)
    corrected_events: List[CollegeEvent] = Field(default_factory=list)
    retry_needed: bool = False


class SessionState(BaseModel):
    session_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    user_id: Optional[str] = None
    chat_id: Optional[str] = None
    message_id: Optional[str] = None
    current_step: str = "router"
    extracted_events: List[CollegeEvent] = Field(default_factory=list)
    validated_events: List[CollegeEvent] = Field(default_factory=list)
    scheduled_events: List[CollegeEvent] = Field(default_factory=list)
    retrieved_context: List[RetrievalResult] = Field(default_factory=list)
    validation_retries: int = 0
    max_validation_retries: int = 2
    errors: List[str] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_step(self, step: str) -> None:
        self.current_step = step
        self.updated_at = datetime.utcnow()

    def add_error(self, error: str) -> None:
        self.errors.append(f"{datetime.utcnow().isoformat()}: {error}")
        self.updated_at = datetime.utcnow()