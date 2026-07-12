"""
User repository with Telegram-specific queries.
"""

from __future__ import annotations

from sqlalchemy import select

from database.models.affiliate import AffiliateTag
from database.models.user import User
from database.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    model = User

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        """Get user by their Telegram ID."""
        return await self.get_one(telegram_id=telegram_id)

    async def get_or_create(
        self,
        telegram_id: int,
        username: str | None = None,
        first_name: str | None = None,
        last_name: str | None = None,
        language_code: str | None = None,
    ) -> tuple[User, bool]:
        """
        Get existing user or create new one.
        Returns (user, created) tuple.
        """
        user = await self.get_by_telegram_id(telegram_id)
        if user is not None:
            # Update info if changed
            changed = False
            if username and user.username != username:
                user.username = username
                changed = True
            if first_name and user.first_name != first_name:
                user.first_name = first_name
                changed = True
            if last_name and user.last_name != last_name:
                user.last_name = last_name
                changed = True
            if changed:
                await self.session.flush()
            return user, False

        user = await self.create(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        return user, True

    async def get_active_users_count(self) -> int:
        """Count active users."""
        return await self.count(is_active=True)

    async def get_all_active(self) -> list[User]:
        """Get all active users (for broadcast)."""
        stmt = select(User).where(User.is_active.is_(True))
        result = await self.session.execute(stmt)
        return list(result.scalars().all())

    async def increment_usage(self, telegram_id: int) -> None:
        """Increment user's usage counter."""
        user = await self.get_by_telegram_id(telegram_id)
        if user:
            user.usage_count += 1
            await self.session.flush()

    async def get_default_tag(self, telegram_id: int) -> AffiliateTag | None:
        """Get user's default affiliate tag."""
        user = await self.get_by_telegram_id(telegram_id)
        if not user:
            return None
        stmt = select(AffiliateTag).where(
            AffiliateTag.user_id == user.id, AffiliateTag.is_default.is_(True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one_or_none()
