"""
Affiliate tag model - Amazon Associates tags per user.
"""

from __future__ import annotations

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin


class AffiliateTag(Base, TimestampMixin):
    __tablename__ = "affiliate_tags"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    tag: Mapped[str] = mapped_column(String(100), nullable=False)
    country_code: Mapped[str] = mapped_column(String(5), default="IN", nullable=False)
    amazon_domain: Mapped[str] = mapped_column(String(50), default="amazon.in", nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    user = relationship("User", back_populates="affiliate_tags")

    def __repr__(self) -> str:
        return f"<AffiliateTag(id={self.id}, tag={self.tag}, domain={self.amazon_domain})>"
