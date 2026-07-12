"""
Processed message model - log of every message processed from source channels.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import (
    BigInteger,
    Boolean,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class ProcessedMessage(Base):
    __tablename__ = "processed_messages"
    __table_args__ = (UniqueConstraint("pipeline_id", "source_channel_id", "source_message_id"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pipeline_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("automation_pipelines.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    source_channel_id: Mapped[int] = mapped_column(BigInteger, nullable=False, index=True)
    source_message_id: Mapped[int] = mapped_column(Integer, nullable=False)
    dest_channel_id: Mapped[int | None] = mapped_column(BigInteger, nullable=True)
    dest_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    original_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    modified_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    asins_found: Mapped[str | None] = mapped_column(Text, nullable=True)  # JSON list
    links_replaced: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    had_media: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    media_type: Mapped[str | None] = mapped_column(String(50), nullable=True)
    status: Mapped[str] = mapped_column(String(20), default="success", nullable=False, index=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)
    processed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<ProcessedMessage(id={self.id}, src={self.source_channel_id}:{self.source_message_id}, status={self.status})>"
