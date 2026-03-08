import pytest
from sqlalchemy import select

from bot.db.models import User


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_create_user(db_session):
    user = User(telegram_id=123, first_name="Alice", username="alice")
    db_session.add(user)
    await db_session.commit()

    result = await db_session.execute(select(User).where(User.telegram_id == 123))
    saved = result.scalar_one()
    assert saved.first_name == "Alice"
    assert saved.is_onboarded is False
