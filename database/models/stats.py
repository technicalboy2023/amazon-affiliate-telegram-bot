"""
Statistics models.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import Date, DateTime, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base


class DailyStat(Base):
    __tablename__ = "daily_stats"
    __table_args__ = (UniqueConstraint("user_id", "pipeline_id", "date"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    pipeline_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("automation_pipelines.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    messages_processed: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    messages_published: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    links_converted: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    duplicates_skipped: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    errors_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_users: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    bot_conversions: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_activity: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    def __repr__(self) -> str:
        return f"<DailyStat(date={self.date}, msgs={self.messages_processed})>"
