# TGpay — Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Создать inline Telegram-бота для запросов на оплату через СБП с генерацией стильных карточек.

**Architecture:** Layered monolith — routers → services → repositories → SQLite. Один Docker-контейнер. aiogram 3 routers + SQLAlchemy 2.0 async ORM + Pillow для карточек.

**Tech Stack:** Python 3.12, aiogram 3, SQLAlchemy 2.0, aiosqlite, Pillow, qrcode, pydantic-settings

**Дизайн-документ:** `docs/plans/2026-03-07-tgpay-design.md`

---

### Task 1: Scaffold проекта

**Files:**
- Create: `pyproject.toml`
- Create: `bot/__init__.py`
- Create: `bot/__main__.py`
- Create: `bot/config.py`
- Create: `bot/app.py`
- Create: `.env.example`
- Create: `bot/routers/__init__.py`

**Step 1: Создать pyproject.toml**

```toml
[project]
name = "tgpay"
version = "0.1.0"
description = "Inline Telegram-бот для запросов на оплату через СБП"
requires-python = ">=3.12"
dependencies = [
    "aiogram>=3.15,<4",
    "sqlalchemy[asyncio]>=2.0,<3",
    "aiosqlite>=0.20",
    "pydantic-settings>=2.0,<3",
    "pillow>=10.0,<11",
    "qrcode[pil]>=7.0,<8",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.0",
    "pytest-asyncio>=0.24",
    "ruff>=0.8",
    "mypy>=1.13",
]
```

**Step 2: Создать bot/config.py**

```python
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    bot_token: str
    database_url: str = "sqlite+aiosqlite:///tgpay.db"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


settings = Settings()
```

**Step 3: Создать bot/app.py**

```python
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.routers import router


def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.include_router(router)
    return dp
```

**Step 4: Создать bot/routers/__init__.py**

```python
from aiogram import Router

router = Router()
```

**Step 5: Создать bot/__main__.py**

```python
import asyncio
import logging

from bot.app import create_bot, create_dispatcher


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    bot = create_bot()
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 6: Создать bot/__init__.py**

```python
```

**Step 7: Создать .env.example**

```
BOT_TOKEN=123456:ABC-DEF...
DATABASE_URL=sqlite+aiosqlite:///tgpay.db
```

**Step 8: Установить зависимости и проверить запуск**

Run: `pip install -e ".[dev]"`
Run: `python -c "from bot.app import create_bot, create_dispatcher; print('OK')"`
Expected: `OK`

**Step 9: Коммит**

```bash
git add pyproject.toml bot/ .env.example
git commit -m "feat: scaffold проекта — config, app, entrypoint"
```

---

### Task 2: Database — модели и engine

**Files:**
- Create: `bot/db/__init__.py`
- Create: `bot/db/engine.py`
- Create: `bot/db/models.py`
- Create: `bot/enums.py`
- Create: `tests/__init__.py`
- Create: `tests/conftest.py`
- Create: `tests/test_models.py`

**Step 1: Создать bot/enums.py**

```python
from enum import StrEnum


class BankName(StrEnum):
    SBER = "sber"
    TINKOFF = "tinkoff"
    ALFA = "alfa"
    VTB = "vtb"
    RAIFFEISEN = "raiffeisen"
```

**Step 2: Создать bot/db/engine.py**

```python
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from bot.config import settings

engine = create_async_engine(settings.database_url, echo=False)
session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def create_tables() -> None:
    from bot.db.models import Base

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
```

**Step 3: Создать bot/db/models.py**

```python
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

    payment_id: Mapped[int] = mapped_column(
        ForeignKey("payments.id"), primary_key=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.telegram_id"), primary_key=True
    )

    payment: Mapped[Payment] = relationship(back_populates="participants")
    user: Mapped[User] = relationship()
```

**Step 4: Создать bot/db/__init__.py**

```python
```

**Step 5: Написать тест — таблицы создаются**

Create `tests/__init__.py` (пустой).

Create `tests/conftest.py`:

```python
import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine, AsyncSession

from bot.db.models import Base


@pytest.fixture
async def db_session():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
```

Create `tests/test_models.py`:

```python
import pytest
from sqlalchemy import select

from bot.db.models import User, Payment, PaymentParticipant


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

    result = await db_session.execute(
        select(Payment).where(Payment.id == payment.id)
    )
    saved = result.scalar_one()
    assert saved.amount == 50000
    assert len(saved.participants) == 1
    assert saved.participants[0].user_id == 2
```

**Step 6: Запустить тесты**

Run: `pytest tests/test_models.py -v`
Expected: 2 PASSED

**Step 7: Коммит**

```bash
git add bot/db/ bot/enums.py tests/
git commit -m "feat: модели данных — User, Payment, PaymentParticipant"
```

---

### Task 3: Database — repositories

**Files:**
- Create: `bot/db/repositories.py`
- Create: `tests/test_repositories.py`

**Step 1: Написать тесты**

Create `tests/test_repositories.py`:

```python
import pytest
from bot.db.repositories import UserRepo, PaymentRepo


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_user_upsert_creates_new(db_session):
    user = await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice", username="alice")
    assert user.telegram_id == 1
    assert user.first_name == "Alice"


async def test_user_upsert_updates_existing(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice", username="alice")
    user = await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice2", username="alice_new")
    assert user.first_name == "Alice2"
    assert user.username == "alice_new"


async def test_user_set_onboarded(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice")
    user = await UserRepo.set_onboarded(db_session, telegram_id=1, phone="+79991234567", bank_name="sber")
    assert user.is_onboarded is True
    assert user.phone == "+79991234567"


async def test_payment_create_and_get(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice")
    payment = await PaymentRepo.create(db_session, creator_id=1, amount=50000, description="за ужин")
    assert payment.id is not None

    fetched = await PaymentRepo.get_by_id(db_session, payment.id)
    assert fetched is not None
    assert fetched.amount == 50000


async def test_payment_add_participant(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Creator")
    await UserRepo.upsert(db_session, telegram_id=2, first_name="Payer")
    payment = await PaymentRepo.create(db_session, creator_id=1, amount=50000, description="тест")

    added = await PaymentRepo.add_participant(db_session, payment_id=payment.id, user_id=2)
    assert added is True

    duplicate = await PaymentRepo.add_participant(db_session, payment_id=payment.id, user_id=2)
    assert duplicate is False
```

**Step 2: Запустить тесты — убедиться что падают**

Run: `pytest tests/test_repositories.py -v`
Expected: FAIL (ModuleNotFoundError)

**Step 3: Реализовать repositories**

Create `bot/db/repositories.py`:

```python
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
            user = User(telegram_id=telegram_id, first_name=first_name, username=username)
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
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def set_inline_message_id(
        session: AsyncSession,
        payment_id: int,
        inline_message_id: str,
    ) -> None:
        result = await session.execute(
            select(Payment).where(Payment.id == payment_id)
        )
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
```

**Step 4: Запустить тесты**

Run: `pytest tests/test_repositories.py -v`
Expected: 5 PASSED

**Step 5: Коммит**

```bash
git add bot/db/repositories.py tests/test_repositories.py
git commit -m "feat: repositories — CRUD для User и Payment"
```

---

### Task 4: Middleware — DB session injection

**Files:**
- Create: `bot/middlewares.py`
- Modify: `bot/app.py`
- Modify: `bot/__main__.py`

**Step 1: Создать bot/middlewares.py**

```python
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import TelegramObject
from sqlalchemy.ext.asyncio import async_sessionmaker


class DbSessionMiddleware(BaseMiddleware):
    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.session_factory = session_factory

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        async with self.session_factory() as session:
            data["session"] = session
            return await handler(event, data)
```

**Step 2: Обновить bot/app.py — подключить middleware**

```python
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from bot.config import settings
from bot.db.engine import session_factory
from bot.middlewares import DbSessionMiddleware
from bot.routers import router


def create_bot() -> Bot:
    return Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher() -> Dispatcher:
    dp = Dispatcher()
    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp.include_router(router)
    return dp
```

**Step 3: Обновить bot/__main__.py — создание таблиц при старте**

```python
import asyncio
import logging

from bot.app import create_bot, create_dispatcher
from bot.db.engine import create_tables


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    await create_tables()
    bot = create_bot()
    dp = create_dispatcher()
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
```

**Step 4: Коммит**

```bash
git add bot/middlewares.py bot/app.py bot/__main__.py
git commit -m "feat: middleware для инъекции DB session в хэндлеры"
```

---

### Task 5: СБП сервис

**Files:**
- Create: `bot/services/__init__.py`
- Create: `bot/services/sbp.py`
- Create: `tests/test_sbp.py`

**Step 1: Написать тесты**

Create `tests/test_sbp.py`:

```python
from bot.services.sbp import build_sbp_deeplink, build_sbp_qr_url

PHONE = "+79991234567"
BANK = "sber"


def test_build_sbp_deeplink():
    link = build_sbp_deeplink(phone=PHONE, bank=BANK, amount=50000)
    assert "qr.nspk.ru" in link or PHONE.replace("+", "") in link
    assert isinstance(link, str)
    assert len(link) > 0


def test_build_sbp_qr_url_contains_amount():
    url = build_sbp_qr_url(phone=PHONE, bank=BANK, amount=50000)
    assert isinstance(url, str)
    assert len(url) > 0


def test_build_sbp_deeplink_different_banks():
    link_sber = build_sbp_deeplink(phone=PHONE, bank="sber", amount=10000)
    link_tink = build_sbp_deeplink(phone=PHONE, bank="tinkoff", amount=10000)
    assert link_sber != link_tink
```

**Step 2: Запустить — убедиться что падают**

Run: `pytest tests/test_sbp.py -v`
Expected: FAIL

**Step 3: Реализовать**

Create `bot/services/__init__.py` (пустой).

Create `bot/services/sbp.py`:

```python
from urllib.parse import urlencode

BANK_SCHEMAS: dict[str, str] = {
    "sber": "https://online.sberbank.ru/CSAFront/index.do",
    "tinkoff": "https://www.tinkoff.ru/cf/",
    "alfa": "https://alfa.me/",
    "vtb": "https://online.vtb.ru/",
    "raiffeisen": "https://pay.raif.ru/",
}

BANK_IDS: dict[str, str] = {
    "sber": "100000000111",
    "tinkoff": "100000000004",
    "alfa": "100000000008",
    "vtb": "100000000005",
    "raiffeisen": "100000000007",
}


def _phone_to_sbp(phone: str) -> str:
    return phone.replace("+", "").replace("-", "").replace(" ", "")


def build_sbp_deeplink(phone: str, bank: str, amount: int) -> str:
    """СБП deeplink для открытия приложения банка.
    amount в копейках.
    """
    phone_clean = _phone_to_sbp(phone)
    params = {
        "type": "02",
        "bank": BANK_IDS.get(bank, "100000000111"),
        "sum": str(amount),
        "cur": "RUB",
        "crc": "0000",
        "st": phone_clean,
    }
    return f"https://qr.nspk.ru/pay?{urlencode(params)}"


def build_sbp_qr_url(phone: str, bank: str, amount: int) -> str:
    """URL для генерации QR-кода (тот же deeplink)."""
    return build_sbp_deeplink(phone=phone, bank=bank, amount=amount)
```

**Step 4: Запустить тесты**

Run: `pytest tests/test_sbp.py -v`
Expected: 3 PASSED

**Step 5: Коммит**

```bash
git add bot/services/ tests/test_sbp.py
git commit -m "feat: СБП сервис — генерация deeplink"
```

---

### Task 6: Card renderer

**Files:**
- Create: `bot/services/card_renderer.py`
- Create: `tests/test_card_renderer.py`
- Add: `assets/fonts/` (скачать Inter font)

**Step 1: Скачать шрифт Inter**

```bash
mkdir -p assets/fonts
curl -L -o assets/fonts/Inter-Bold.ttf "https://github.com/rsms/inter/raw/master/fonts/desktop/Inter-Bold.otf"
```

**Step 2: Написать тесты**

Create `tests/test_card_renderer.py`:

```python
import pytest
from io import BytesIO
from PIL import Image

from bot.services.card_renderer import render_card


def test_render_card_returns_bytes():
    result = render_card(
        amount=50000,
        description="за ужин",
        creator_username="alice",
        sbp_url="https://qr.nspk.ru/pay?test=1",
        participants=[],
    )
    assert isinstance(result, BytesIO)


def test_render_card_is_valid_image():
    result = render_card(
        amount=50000,
        description="за ужин",
        creator_username="alice",
        sbp_url="https://qr.nspk.ru/pay?test=1",
        participants=[],
    )
    img = Image.open(result)
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_render_card_with_participants():
    result = render_card(
        amount=50000,
        description="за ужин",
        creator_username="alice",
        sbp_url="https://qr.nspk.ru/pay?test=1",
        participants=["bob", "charlie"],
    )
    img = Image.open(result)
    assert img.size[0] > 0
```

**Step 3: Запустить — убедиться что падают**

Run: `pytest tests/test_card_renderer.py -v`
Expected: FAIL

**Step 4: Реализовать card_renderer**

Create `bot/services/card_renderer.py`:

```python
from io import BytesIO
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "Inter-Bold.ttf"

CARD_WIDTH = 600
CARD_HEIGHT = 400
BG_COLOR = "#1a1a2e"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#ffffff"
PAID_COLOR = "#4ecca3"
QR_SIZE = 140


def _format_amount(kopecks: int) -> str:
    rubles = kopecks // 100
    kop = kopecks % 100
    if kop:
        return f"{rubles},{kop:02d} ₽"
    return f"{rubles} ₽"


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except OSError:
        return ImageFont.load_default()


def _generate_qr(data: str) -> Image.Image:
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="#ffffff", back_color=BG_COLOR).convert("RGBA")


def render_card(
    amount: int,
    description: str,
    creator_username: str | None,
    sbp_url: str,
    participants: list[str],
) -> BytesIO:
    img = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_big = _load_font(48)
    font_mid = _load_font(20)
    font_small = _load_font(16)

    # Сумма
    amount_text = _format_amount(amount)
    bbox = draw.textbbox((0, 0), amount_text, font=font_big)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, 30),
        amount_text,
        fill=TEXT_COLOR,
        font=font_big,
    )

    # Описание
    bbox = draw.textbbox((0, 0), description, font=font_mid)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, 90),
        description,
        fill="#aaaaaa",
        font=font_mid,
    )

    # QR-код
    qr_img = _generate_qr(sbp_url)
    qr_img = qr_img.resize((QR_SIZE, QR_SIZE))
    qr_x = (CARD_WIDTH - QR_SIZE) // 2
    qr_y = 130
    img.paste(qr_img, (qr_x, qr_y))

    # Участники
    if participants:
        y = qr_y + QR_SIZE + 15
        parts_text = "  ".join(f"✓ @{p}" for p in participants)
        bbox = draw.textbbox((0, 0), parts_text, font=font_small)
        text_w = bbox[2] - bbox[0]
        draw.text(
            ((CARD_WIDTH - text_w) / 2, y),
            parts_text,
            fill=PAID_COLOR,
            font=font_small,
        )

    # Футер
    footer = f"@{creator_username} • TGpay" if creator_username else "TGpay"
    bbox = draw.textbbox((0, 0), footer, font=font_small)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, CARD_HEIGHT - 35),
        footer,
        fill="#666666",
        font=font_small,
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
```

**Step 5: Запустить тесты**

Run: `pytest tests/test_card_renderer.py -v`
Expected: 3 PASSED

**Step 6: Коммит**

```bash
git add bot/services/card_renderer.py tests/test_card_renderer.py assets/
git commit -m "feat: генерация карточки оплаты — Pillow + QR"
```

---

### Task 7: Payment сервис

**Files:**
- Create: `bot/services/payment.py`
- Create: `tests/test_payment_service.py`

**Step 1: Написать тесты**

Create `tests/test_payment_service.py`:

```python
import pytest
from unittest.mock import AsyncMock, patch
from io import BytesIO

from bot.services.payment import PaymentService
from bot.db.repositories import UserRepo


pytestmark = pytest.mark.asyncio(loop_scope="function")


async def test_create_payment(db_session):
    await UserRepo.upsert(db_session, telegram_id=1, first_name="Alice", username="alice")
    await UserRepo.set_onboarded(db_session, telegram_id=1, phone="+79991234567", bank_name="sber")

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
    await UserRepo.set_onboarded(db_session, telegram_id=1, phone="+79991234567", bank_name="sber")
    await UserRepo.upsert(db_session, telegram_id=2, first_name="Payer", username="payer")

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
    await UserRepo.set_onboarded(db_session, telegram_id=1, phone="+79991234567", bank_name="sber")
    await UserRepo.upsert(db_session, telegram_id=2, first_name="Payer", username="payer")

    payment, _ = await PaymentService.create_payment(
        session=db_session, creator_id=1, amount=50000, description="тест"
    )

    await PaymentService.mark_paid(session=db_session, payment_id=payment.id, user_id=2)
    result = await PaymentService.mark_paid(session=db_session, payment_id=payment.id, user_id=2)
    assert result.added is False
```

**Step 2: Запустить — убедиться что падают**

Run: `pytest tests/test_payment_service.py -v`
Expected: FAIL

**Step 3: Реализовать**

Create `bot/services/payment.py`:

```python
from dataclasses import dataclass
from io import BytesIO

from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import PaymentRepo, UserRepo
from bot.services.card_renderer import render_card
from bot.services.sbp import build_sbp_qr_url
from bot.db.models import Payment


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
        added = await PaymentRepo.add_participant(session, payment_id=payment_id, user_id=user_id)
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
```

**Step 4: Запустить тесты**

Run: `pytest tests/test_payment_service.py -v`
Expected: 3 PASSED

**Step 5: Коммит**

```bash
git add bot/services/payment.py tests/test_payment_service.py
git commit -m "feat: PaymentService — создание и подтверждение платежей"
```

---

### Task 8: Онбординг FSM

**Files:**
- Create: `bot/states.py`
- Create: `bot/keyboards.py`
- Create: `bot/routers/private.py`
- Modify: `bot/routers/__init__.py`

**Step 1: Создать bot/states.py**

```python
from aiogram.fsm.state import State, StatesGroup


class OnboardingStates(StatesGroup):
    waiting_phone = State()
    waiting_bank = State()
```

**Step 2: Создать bot/keyboards.py**

```python
from aiogram.types import InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from bot.enums import BankName

BANK_LABELS: dict[str, str] = {
    BankName.SBER: "Сбер",
    BankName.TINKOFF: "Т-Банк",
    BankName.ALFA: "Альфа",
    BankName.VTB: "ВТБ",
    BankName.RAIFFEISEN: "Райффайзен",
}


def bank_selection_keyboard() -> InlineKeyboardBuilder:
    builder = InlineKeyboardBuilder()
    for bank_id, label in BANK_LABELS.items():
        builder.add(InlineKeyboardButton(text=label, callback_data=f"bank:{bank_id}"))
    builder.adjust(2)
    return builder
```

**Step 3: Создать bot/routers/private.py**

```python
import re

from aiogram import F, Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from bot.db.repositories import UserRepo
from bot.keyboards import bank_selection_keyboard
from bot.states import OnboardingStates

router = Router()
PHONE_RE = re.compile(r"^\+7\d{10}$")


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext, session: AsyncSession) -> None:
    await UserRepo.upsert(
        session,
        telegram_id=message.from_user.id,
        first_name=message.from_user.first_name,
        username=message.from_user.username,
    )

    user = await UserRepo.get_by_id(session, message.from_user.id)
    if user.is_onboarded:
        await message.answer(
            "Ты уже настроен! Используй <b>@TGpayBot сумма описание</b> в любом чате."
        )
        return

    await state.set_state(OnboardingStates.waiting_phone)
    await message.answer(
        "Привет! Я помогу создавать запросы на оплату через СБП.\n\n"
        "Введи номер телефона в формате <b>+7XXXXXXXXXX</b>:"
    )


@router.message(OnboardingStates.waiting_phone)
async def process_phone(message: Message, state: FSMContext) -> None:
    phone = message.text.strip()
    if not PHONE_RE.match(phone):
        await message.answer("Неверный формат. Введи номер в формате <b>+7XXXXXXXXXX</b>:")
        return

    await state.update_data(phone=phone)
    await state.set_state(OnboardingStates.waiting_bank)

    kb = bank_selection_keyboard()
    await message.answer("Выбери банк для приёма СБП:", reply_markup=kb.as_markup())


@router.callback_query(OnboardingStates.waiting_bank, F.data.startswith("bank:"))
async def process_bank(callback: CallbackQuery, state: FSMContext, session: AsyncSession) -> None:
    bank_name = callback.data.split(":")[1]
    data = await state.get_data()
    phone = data["phone"]

    await UserRepo.set_onboarded(
        session,
        telegram_id=callback.from_user.id,
        phone=phone,
        bank_name=bank_name,
    )

    await state.clear()
    await callback.message.edit_text(
        "Готово! Теперь используй <b>@TGpayBot сумма описание</b> в любом чате.\n\n"
        "Пример: <code>@TGpayBot 500 за ужин</code>"
    )
    await callback.answer()
```

**Step 4: Обновить bot/routers/__init__.py**

```python
from aiogram import Router

from bot.routers.private import router as private_router

router = Router()
router.include_router(private_router)
```

**Step 5: Коммит**

```bash
git add bot/states.py bot/keyboards.py bot/routers/
git commit -m "feat: онбординг — FSM для ввода телефона и выбора банка"
```

---

### Task 9: Inline query + chosen result

**Files:**
- Create: `bot/callback_data.py`
- Create: `bot/routers/inline.py`
- Modify: `bot/routers/__init__.py`

**Step 1: Создать bot/callback_data.py**

```python
from aiogram.filters.callback_data import CallbackData


class PaymentCallback(CallbackData, prefix="pay"):
    payment_id: int
    action: str  # "paid"
```

**Step 2: Создать bot/routers/inline.py**

```python
import re

from aiogram import Bot, Router
from aiogram.types import (
    BufferedInputFile,
    ChosenInlineResult,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    InlineQuery,
    InlineQueryResultArticle,
    InlineQueryResultsButton,
    InputTextMessageContent,
)
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import PaymentCallback
from bot.db.repositories import PaymentRepo, UserRepo
from bot.services.payment import PaymentService

router = Router()

QUERY_RE = re.compile(r"^(\d+)\s*(.*)?$")


def _parse_query(text: str) -> tuple[int, str] | None:
    m = QUERY_RE.match(text.strip())
    if not m:
        return None
    amount_rubles = int(m.group(1))
    description = (m.group(2) or "").strip() or "Оплата"
    return amount_rubles * 100, description


@router.inline_query()
async def on_inline_query(inline_query: InlineQuery, session: AsyncSession) -> None:
    user = await UserRepo.get_by_id(session, inline_query.from_user.id)

    if not user or not user.is_onboarded:
        await inline_query.answer(
            results=[],
            button=InlineQueryResultsButton(
                text="Сначала настрой бота →",
                start_parameter="onboarding",
            ),
            cache_time=5,
            is_personal=True,
        )
        return

    parsed = _parse_query(inline_query.query)
    if not parsed:
        await inline_query.answer(results=[], cache_time=5, is_personal=True)
        return

    amount, description = parsed
    amount_text = f"{amount // 100} ₽"

    results = [
        InlineQueryResultArticle(
            id=f"{inline_query.from_user.id}:{amount}:{description}",
            title=f"Запросить {amount_text}",
            description=description,
            input_message_content=InputTextMessageContent(
                message_text=f"Загрузка платежа {amount_text}..."
            ),
        )
    ]

    await inline_query.answer(results=results, cache_time=5, is_personal=True)


@router.chosen_inline_result()
async def on_chosen_result(
    chosen: ChosenInlineResult, bot: Bot, session: AsyncSession
) -> None:
    parsed = _parse_query(chosen.query)
    if not parsed:
        return

    amount, description = parsed

    payment, card_bytes = await PaymentService.create_payment(
        session=session,
        creator_id=chosen.from_user.id,
        amount=amount,
        description=description,
    )

    if chosen.inline_message_id:
        await PaymentRepo.set_inline_message_id(
            session, payment.id, chosen.inline_message_id
        )

    keyboard = InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Я оплатил ✓",
                    callback_data=PaymentCallback(
                        payment_id=payment.id, action="paid"
                    ).pack(),
                ),
            ]
        ]
    )

    photo = BufferedInputFile(card_bytes.read(), filename="card.png")

    from aiogram.types import InputMediaPhoto

    if chosen.inline_message_id:
        await bot.edit_message_media(
            inline_message_id=chosen.inline_message_id,
            media=InputMediaPhoto(media=photo),
            reply_markup=keyboard,
        )
```

**Step 3: Обновить bot/routers/__init__.py**

```python
from aiogram import Router

from bot.routers.inline import router as inline_router
from bot.routers.private import router as private_router

router = Router()
router.include_router(private_router)
router.include_router(inline_router)
```

**Step 4: Коммит**

```bash
git add bot/callback_data.py bot/routers/
git commit -m "feat: inline query — парсинг запроса и отправка карточки"
```

---

### Task 10: Callback handler — "Я оплатил"

**Files:**
- Create: `bot/routers/callbacks.py`
- Modify: `bot/routers/__init__.py`

**Step 1: Создать bot/routers/callbacks.py**

```python
from aiogram import Bot, Router
from aiogram.types import BufferedInputFile, CallbackQuery, InputMediaPhoto
from sqlalchemy.ext.asyncio import AsyncSession

from bot.callback_data import PaymentCallback
from bot.db.repositories import UserRepo
from bot.services.payment import PaymentService

router = Router()


@router.callback_query(PaymentCallback.filter())
async def on_payment_callback(
    callback: CallbackQuery,
    callback_data: PaymentCallback,
    bot: Bot,
    session: AsyncSession,
) -> None:
    if callback_data.action != "paid":
        await callback.answer()
        return

    await UserRepo.upsert(
        session,
        telegram_id=callback.from_user.id,
        first_name=callback.from_user.first_name,
        username=callback.from_user.username,
    )

    result = await PaymentService.mark_paid(
        session=session,
        payment_id=callback_data.payment_id,
        user_id=callback.from_user.id,
    )

    if not result.added:
        await callback.answer("Ты уже отметился!")
        return

    if result.card_bytes and callback.inline_message_id:
        photo = BufferedInputFile(result.card_bytes.read(), filename="card.png")

        from bot.callback_data import PaymentCallback as PC

        keyboard = callback.message.reply_markup if callback.message else None

        await bot.edit_message_media(
            inline_message_id=callback.inline_message_id,
            media=InputMediaPhoto(media=photo),
            reply_markup=keyboard,
        )

    await callback.answer("Оплата отмечена ✓")
```

**Step 2: Обновить bot/routers/__init__.py**

```python
from aiogram import Router

from bot.routers.callbacks import router as callbacks_router
from bot.routers.inline import router as inline_router
from bot.routers.private import router as private_router

router = Router()
router.include_router(private_router)
router.include_router(inline_router)
router.include_router(callbacks_router)
```

**Step 3: Коммит**

```bash
git add bot/routers/
git commit -m "feat: callback — обработка кнопки 'Я оплатил'"
```

---

### Task 11: Dockerfile

**Files:**
- Create: `Dockerfile`
- Create: `.dockerignore`

**Step 1: Создать Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY pyproject.toml .
RUN pip install --no-cache-dir .

COPY bot/ bot/
COPY assets/ assets/

CMD ["python", "-m", "bot"]
```

**Step 2: Создать .dockerignore**

```
.git
.env
__pycache__
*.pyc
tests/
docs/
.ruff_cache
.mypy_cache
*.db
```

**Step 3: Проверить сборку**

Run: `docker build -t tgpay .`
Expected: Successfully built

**Step 4: Коммит**

```bash
git add Dockerfile .dockerignore
git commit -m "feat: Dockerfile для one-liner запуска"
```

---

### Task 12: CI + README + CLAUDE.md

**Files:**
- Create: `.github/workflows/ci.yml`
- Create: `README.md`
- Create: `CLAUDE.md`
- Create: `LICENSE`

**Step 1: Создать .github/workflows/ci.yml**

```yaml
name: CI

on:
  push:
    branches: [main]
  pull_request:
    branches: [main]

jobs:
  lint-and-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"

      - name: Установить зависимости
        run: pip install -e ".[dev]"

      - name: Ruff lint
        run: ruff check bot/ tests/

      - name: Ruff format
        run: ruff format --check bot/ tests/

      - name: Mypy
        run: mypy bot/ --ignore-missing-imports

      - name: Pytest
        run: pytest tests/ -v

  docker:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Docker build
        run: docker build -t tgpay .
```

**Step 2: Создать README.md**

Написать README по макету из дизайн-документа (секция GitHub-стратегия). Включить:
- Hero-заголовок
- Быстрый старт (docker run)
- Возможности
- Архитектура
- Стек
- Секция "Собран с помощью AI"

**Step 3: Создать CLAUDE.md**

```markdown
# TGpay

## Обзор
Inline Telegram-бот для запросов на оплату через СБП.

## Стек
- Python 3.12, aiogram 3, SQLAlchemy 2.0 async, aiosqlite, Pillow, qrcode
- pydantic-settings для конфигурации

## Архитектура
Layered monolith: `bot/routers/` → `bot/services/` → `bot/db/repositories.py` → SQLite.
Слои не пересекаются. Handlers не обращаются к БД напрямую.

## Конвенции
- Язык кода: Python, комментарии и строки на русском
- Форматтер: ruff format
- Линтер: ruff check
- Типы: mypy --ignore-missing-imports
- Тесты: pytest, async тесты через pytest-asyncio
- amount всегда в копейках (int)
- Коммиты на русском: "feat: описание", "fix: описание"

## Команды
- `pip install -e ".[dev]"` — установка
- `pytest tests/ -v` — тесты
- `ruff check bot/ tests/` — линт
- `ruff format bot/ tests/` — формат
- `python -m bot` — запуск (нужен .env с BOT_TOKEN)

## Структура
См. `docs/plans/2026-03-07-tgpay-design.md`
```

**Step 4: Создать LICENSE (MIT)**

**Step 5: Коммит**

```bash
git add .github/ README.md CLAUDE.md LICENSE
git commit -m "feat: CI, README, CLAUDE.md, лицензия"
```

---

## Порядок выполнения

| # | Task | Зависит от |
|---|------|-----------|
| 1 | Scaffold проекта | — |
| 2 | DB модели + engine | 1 |
| 3 | Repositories | 2 |
| 4 | Middleware DB session | 3 |
| 5 | СБП сервис | 1 |
| 6 | Card renderer | 1 |
| 7 | Payment сервис | 3, 5, 6 |
| 8 | Онбординг FSM | 3, 4 |
| 9 | Inline query + chosen result | 7 |
| 10 | Callback "Я оплатил" | 7 |
| 11 | Dockerfile | все |
| 12 | CI + README | все |

Параллельно можно: Task 5 + Task 6 (не зависят друг от друга).
