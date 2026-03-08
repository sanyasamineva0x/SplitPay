from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import User


class UserRepo:
    @staticmethod
    async def upsert(
        session: AsyncSession,
        telegram_id: int,
        first_name: str,
        username: str | None = None,
    ) -> User:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one_or_none()
        if user is None:
            user = User(
                telegram_id=telegram_id, first_name=first_name, username=username
            )
            session.add(user)
        else:
            user.first_name = first_name
            user.username = username
        await session.commit()
        return user

    @staticmethod
    async def get_by_id(session: AsyncSession, telegram_id: int) -> User | None:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def set_onboarded(
        session: AsyncSession,
        telegram_id: int,
        phone: str,
        bank_name: str,
    ) -> User:
        result = await session.execute(
            select(User).where(User.telegram_id == telegram_id)
        )
        user = result.scalar_one()
        user.phone = phone
        user.bank_name = bank_name
        user.is_onboarded = True
        await session.commit()
        return user
