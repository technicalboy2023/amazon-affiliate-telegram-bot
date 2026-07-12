"""
Telegram account repository with user-scoped queries.
"""

from __future__ import annotations

from sqlalchemy import select

from database.models.telegram_account import TelegramAccount
from database.repositories.base import BaseRepository


class TelegramAccountRepository(BaseRepository[TelegramAccount]):
    model = TelegramAccount

    async def get_user_account(self, user_id: int, account_id: int) -> TelegramAccount | None:
        """Get a Telegram account owned by a user."""
        return await self.get_one(user_id=user_id, id=account_id)

    async def get_active_accounts(self, user_id: int) -> list[TelegramAccount]:
        """Get active Telegram accounts for a user."""
        stmt = select(TelegramAccount).where(
            TelegramAccount.user_id == user_id, TelegramAccount.is_active.is_(True)
        )
        result = await self.session.execute(stmt)
        return list(result.scalars().all())
