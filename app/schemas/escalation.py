from pydantic import BaseModel, Field


class EscalationRequest(BaseModel):
    session_id: str
    channel: str = "web"
    priority: str = Field(default="medium")
    reason: str = Field(min_length=2, max_length=256)
    conversation_excerpt: str = Field(min_length=1)


class EscalationResponse(BaseModel):
    ticket_id: str
    status: str
