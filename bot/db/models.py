from __future__ import annotations

from datetime import datetime

from sqlalchemy import func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(AsyncAttrs, DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class User(TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None]
    first_name: Mapped[str]
    phone: Mapped[str | None]
    bank_name: Mapped[str | None]
    is_onboarded: Mapped[bool] = mapped_column(default=False)
