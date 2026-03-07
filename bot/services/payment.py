from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.models import Payment
from bot.db.repositories import PaymentRepo, UserRepo
from bot.services.card_renderer import render_card
from bot.services.sbp import build_sbp_qr_url


@dataclass
class MarkPaidResult:
    added: bool
    card_bytes: BytesIO | None


class PaymentService:
    @staticmethod
    async def create_payment(
        session: AsyncSession,
        creator_id: int,
        amount: int,
        description: str,
    ) -> tuple[Payment, BytesIO]:
        """Создать платёж и сгенерировать карточку."""
        creator = await UserRepo.get_by_id(session, creator_id)
        payment = await PaymentRepo.create(
            session, creator_id=creator_id, amount=amount, description=description
        )

        sbp_url = build_sbp_qr_url(
            phone=creator.phone, bank=creator.bank_name, amount=amount
        )
        card_bytes = render_card(
            amount=amount,
            description=description,
            creator_username=creator.username,
            sbp_url=sbp_url,
            participants=[],
        )

        return payment, card_bytes

    @staticmethod
    async def mark_paid(
        session: AsyncSession,
        payment_id: int,
        user_id: int,
    ) -> MarkPaidResult:
        """Отметить участника как оплатившего и перерисовать карточку."""
        added = await PaymentRepo.add_participant(
            session, payment_id=payment_id, user_id=user_id
        )
        if not added:
            return MarkPaidResult(added=False, card_bytes=None)

        payment = await PaymentRepo.get_by_id(session, payment_id)
        creator = await UserRepo.get_by_id(session, payment.creator_id)

        sbp_url = build_sbp_qr_url(
            phone=creator.phone, bank=creator.bank_name, amount=payment.amount
        )

        participant_names = []
        for p in payment.participants:
            u = await UserRepo.get_by_id(session, p.user_id)
            participant_names.append(u.username or u.first_name)

        card_bytes = render_card(
            amount=payment.amount,
            description=payment.description,
            creator_username=creator.username,
            sbp_url=sbp_url,
            participants=participant_names,
        )

        return MarkPaidResult(added=True, card_bytes=card_bytes)
