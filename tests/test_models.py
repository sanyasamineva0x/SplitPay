import pytest
from sqlalchemy import select

from bot.db.models import Payment, PaymentParticipant, User


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_create_user(db_session):
    user = User(telegram_id=123, first_name="Alice", username="alice")
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.telegram_id == 123))
    saved = result.scalar_one()
    assert saved.first_name == "Alice"
    assert saved.is_onboarded is False


async def test_create_payment_with_participant(db_session):
    creator = User(telegram_id=1, first_name="Creator")
    payer = User(telegram_id=2, first_name="Payer")
    db_session.add_all([creator, payer])
    await db_session.flush()

    payment = Payment(creator_id=1, amount=50000, description="за ужин")
    db_session.add(payment)
    await db_session.flush()

    participant = PaymentParticipant(payment_id=payment.id, user_id=2)
    db_session.add(participant)
    await db_session.commit()

    result = await db_session.execute(select(Payment).where(Payment.id == payment.id))
    saved = result.scalar_one()
    assert saved.amount == 50000
    assert len(saved.participants) == 1
    assert saved.participants[0].user_id == 2
