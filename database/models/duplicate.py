"""
Duplicate cache model - tracks seen ASINs to avoid re-posting.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class DuplicateCache(Base):
    __tablename__ = "duplicate_cache"
    __table_args__ = (UniqueConstraint("pipeline_id", "asin"),)

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
    asin: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    source_channel_id: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    source_message_id: Mapped[int | None] = mapped_column(Integer, nullable=True)
    first_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    def __repr__(self) -> str:
        return f"<DuplicateCache(asin={self.asin}, channel={self.source_channel_id})>"
