"""Chat schemas (Pydantic v2)."""

from typing import Optional, Any
from datetime import datetime
from pydantic import BaseModel, ConfigDict, Field


class ChatMessageResponse(BaseModel):
    id: int
    session_id: str
    sender: str
    query_text: str
    response_text: Optional[str] = None
    audio_url: Optional[str] = None
    image_url: Optional[str] = None
    system_context_snapshot: Optional[dict[str, Any]] = None
    hazard_state: Optional[str] = None
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ChatSessionResponse(BaseModel):
    id: str
    device_id: str
    plot_id: Optional[int] = None
    title: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: list[ChatMessageResponse] = Field(default_factory=list)

    model_config = ConfigDict(from_attributes=True)


class ChatReceptorResponse(BaseModel):
    session_id: str
    reply_text: str
    audio_base64_url: Optional[str] = None
    hazard_state: str
    injected_context: dict[str, Any]

