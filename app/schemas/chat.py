from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

Channel = Literal["web", "sms", "voice"]


class CreateSessionRequest(BaseModel):
    channel: Channel = "web"
    consent_to_contact: bool = False
    phone_number: str | None = None


class SessionResponse(BaseModel):
    session_id: str
    channel: Channel
    consent_to_contact: bool
    created_at: datetime


class ChatMessageRequest(BaseModel):
    session_id: str
    channel: Channel = "web"
    text: str = Field(min_length=1, max_length=4000)
    consent_to_contact: bool | None = None


class ChatReference(BaseModel):
    source_url: str
    title: str
    snippet: str


class ChatMessageResponse(BaseModel):
    session_id: str
    channel: Channel
    intent: str
    confidence: float
    escalated: bool
    response_text: str
    references: list[ChatReference] = Field(default_factory=list)
