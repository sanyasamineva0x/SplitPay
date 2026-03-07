from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Payment, PaymentParticipant, User


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


class PaymentRepo:
    @staticmethod
    async def create(
        session: AsyncSession,
        creator_id: int,
        amount: int,
        description: str,
    ) -> Payment:
        payment = Payment(creator_id=creator_id, amount=amount, description=description)
        session.add(payment)
        await session.commit()
        return payment

    @staticmethod
    async def get_by_id(session: AsyncSession, payment_id: int) -> Payment | None:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def set_inline_message_id(
        session: AsyncSession,
        payment_id: int,
        inline_message_id: str,
    ) -> None:
        result = await session.execute(select(Payment).where(Payment.id == payment_id))
        payment = result.scalar_one()
        payment.inline_message_id = inline_message_id
        await session.commit()

    @staticmethod
    async def add_participant(
        session: AsyncSession,
        payment_id: int,
        user_id: int,
    ) -> bool:
        participant = PaymentParticipant(payment_id=payment_id, user_id=user_id)
        session.add(participant)
        try:
            await session.commit()
            return True
        except IntegrityError:
            await session.rollback()
            return False
