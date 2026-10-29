"""Chat Session and Message history models.

Provides multi-turn conversational memory with environmental context snapshots.
"""

from datetime import datetime, timezone
import uuid
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    device_id = Column(String(128), ForeignKey("device_profiles.device_id", ondelete="CASCADE"), nullable=False, index=True)
    plot_id = Column(Integer, ForeignKey("farm_plots.id", ondelete="SET NULL"), nullable=True)
    title = Column(String(200), nullable=True, default="Agricultural Consultation")
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    device = relationship("DeviceProfile", back_populates="chat_sessions")
    messages = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.id")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = Column(Integer, primary_key=True, autoincrement=True, index=True)
    session_id = Column(String(36), ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    sender = Column(String(20), nullable=False)  # USER, ASSISTANT, SYSTEM
    query_text = Column(Text, nullable=False)
    response_text = Column(Text, nullable=True)
    audio_url = Column(String(255), nullable=True)
    image_url = Column(String(255), nullable=True)
    system_context_snapshot = Column(JSON, nullable=True)
    hazard_state = Column(String(32), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), nullable=False)

    session = relationship("ChatSession", back_populates="messages")

