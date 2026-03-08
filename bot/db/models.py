from __future__ import annotations

from datetime import datetime

from sqlalchemy import ForeignKey, func
from sqlalchemy.ext.asyncio import AsyncAttrs
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


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


class Expense(TimestampMixin, Base):
    __tablename__ = "expenses"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    amount: Mapped[int]  # сумма в копейках
    description: Mapped[str]
    inline_message_id: Mapped[str | None] = mapped_column(index=True)
    card_file_id: Mapped[str | None]

    creator: Mapped[User] = relationship(foreign_keys=[creator_id])
    participants: Mapped[list[ExpenseParticipant]] = relationship(
        back_populates="expense", lazy="selectin"
    )


class ExpenseParticipant(Base):
    __tablename__ = "expense_participants"

    expense_id: Mapped[int] = mapped_column(ForeignKey("expenses.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id"), primary_key=True
    )
    amount: Mapped[int]  # доля в копейках
    is_settled: Mapped[bool] = mapped_column(default=False)
    settled_at: Mapped[datetime | None] = mapped_column(default=None)

    expense: Mapped[Expense] = relationship(back_populates="participants")
    user: Mapped[User] = relationship()
