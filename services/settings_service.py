import logging

from sqlalchemy import select

from database.models.settings import AppSetting

logger = logging.getLogger(__name__)


class SettingsService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def get(self, key: str, default: str = "") -> str:
        async with self.session_factory() as session:
            stmt = select(AppSetting).where(AppSetting.key == key)
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()
            if setting is None:
                return default
            return setting.value

    async def set(self, key: str, value: str) -> None:
        async with self.session_factory() as session:
            stmt = select(AppSetting).where(AppSetting.key == key)
            result = await session.execute(stmt)
            setting = result.scalar_one_or_none()
            if setting is None:
                setting = AppSetting(key=key, value=value)
                session.add(setting)
            else:
                setting.value = value
            await session.commit()

    async def get_source_channels(self) -> list[str]:
        value = await self.get("source_channels", "")
        if not value:
            return []
        return [c.strip() for c in value.split(",") if c.strip()]

    async def get_affiliate_tag(self) -> str:
        return await self.get("affiliate_tag", "")

    async def get_dest_channel(self) -> str:
        return await self.get("dest_channel", "")
