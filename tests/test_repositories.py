import pytest

from bot.db.repositories import UserRepo


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_user_upsert_creates_new(db_session):
    user = await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Alice", username="alice"
    )
    assert user.telegram_id == 1
    assert user.first_name == "Alice"


async def test_user_upsert_updates_existing(db_session):
    await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Alice", username="alice"
    )
    user = await UserRepo.upsert(
        db_session, telegram_id=1, first_name="Alice2", username="alice_new"
    )
    assert user.first_name == "Alice2"
    assert user.username == "alice_new"


async def test_user_set_onboarded(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice")
    user = await UserRepo.set_onboarded(
        db_session, telegram_id=1, phone="+79991234567", bank_name="sber"
    )
    assert user.is_onboarded is True
    assert user.phone == "+79991234567"
