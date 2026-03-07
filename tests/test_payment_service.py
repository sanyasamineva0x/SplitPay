import pytest
from io import BytesIO

from bot.services.payment import PaymentService
from bot.db.repositories import UserRepo


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_create_payment(db_session):
    await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Alice", username="alice"
    )
    await UserRepo.set_onboarded(
        db_session, telegram_id=1, phone="+79991234567", bank_name="sber"
    )

    payment, card_bytes = await PaymentService.create_payment(
        session=db_session,
        creator_id=1,
        amount=50000,
        description="за ужин",
    )

    assert payment.amount == 50000
    assert isinstance(card_bytes, BytesIO)


async def test_mark_paid(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Creator")
    await UserRepo.set_onboarded(
        db_session, telegram_id=1, phone="+79991234567", bank_name="sber"
    )
    await UserRepo.upsert(
        db_session, telegram_id=2, first_name="Payer", username="payer"
    )

    payment, _ = await PaymentService.create_payment(
        session=db_session, creator_id=1, amount=50000, description="тест"
    )

    result = await PaymentService.mark_paid(
        session=db_session, payment_id=payment.id, user_id=2
    )
    assert result.added is True
    assert isinstance(result.card_bytes, BytesIO)


async def test_mark_paid_duplicate(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Creator")
    await UserRepo.set_onboarded(
        db_session, telegram_id=1, phone="+79991234567", bank_name="sber"
    )
    await UserRepo.upsert(
        db_session, telegram_id=2, first_name="Payer", username="payer"
    )

    payment, _ = await PaymentService.create_payment(
        session=db_session, creator_id=1, amount=50000, description="тест"
    )

    await PaymentService.mark_paid(session=db_session, payment_id=payment.id, user_id=2)
    result = await PaymentService.mark_paid(
        session=db_session, payment_id=payment.id, user_id=2
    )
    assert result.added is False
