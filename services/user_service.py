import logging

from sqlalchemy import select

from database.models.pipeline import AutomationPipeline
from database.models.user import User

logger = logging.getLogger(__name__)


class UserService:
    def __init__(self, session_factory):
        self.session_factory = session_factory

    async def ensure_admin(self, telegram_id: int, username: str | None = None, first_name: str | None = None) -> User:
        async with self.session_factory() as session:
            stmt = select(User).where(User.telegram_id == telegram_id)
            result = await session.execute(stmt)
            user = result.scalar_one_or_none()
            if user is None:
                user = User(
                    telegram_id=telegram_id,
                    username=username,
                    first_name=first_name,
                    is_admin=True,
                    is_active=True,
                )
                session.add(user)
                await session.commit()
                await session.refresh(user)
                logger.info("Created admin user: tg_id=%d", telegram_id)
            else:
                if not user.is_admin:
                    user.is_admin = True
                    await session.commit()
            return user

    async def ensure_default_setup(self, user_id: int, affiliate_tag: str = "", amazon_domain: str = "amazon.in") -> AutomationPipeline:
        async with self.session_factory() as session:
            stmt = select(AutomationPipeline).where(
                AutomationPipeline.user_id == user_id,
                AutomationPipeline.status == "active",
            )
            result = await session.execute(stmt)
            pipeline = result.scalar_one_or_none()
            if pipeline is not None:
                return pipeline

            pipeline = AutomationPipeline(
                user_id=user_id,
                name="default",
                status="active",
            )
            session.add(pipeline)
            await session.commit()
            await session.refresh(pipeline)
            logger.info("Created default pipeline for user_id=%d (id=%d)", user_id, pipeline.id)
            return pipeline