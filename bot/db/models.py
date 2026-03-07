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

    created_payments: Mapped[list[Payment]] = relationship(
        back_populates="creator", foreign_keys="Payment.creator_id"
    )


class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    amount: Mapped[int]
    description: Mapped[str]
    inline_message_id: Mapped[str | None] = mapped_column(index=True)
    card_file_id: Mapped[str | None]

    creator: Mapped[User] = relationship(
        back_populates="created_payments", foreign_keys=[creator_id]
    )
    participants: Mapped[list[PaymentParticipant]] = relationship(
        back_populates="payment", lazy="selectin"
    )


class PaymentParticipant(TimestampMixin, Base):
    __tablename__ = "payment_participants"

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id"), primary_key=True
    )

    payment: Mapped[Payment] = relationship(back_populates="participants")
    user: Mapped[User] = relationship()
