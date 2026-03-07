# TGpay — Дизайн-документ

> Inline Telegram-бот для мгновенных запросов на оплату через СБП

## Обзор

TGpay — inline-бот для Telegram. Пользователь пишет `@TGpayBot 500 за ужин` в любом чате, бот генерирует стильную карточку с QR-кодом СБП. Любой участник чата может нажать "Я оплатил" — карточка обновляется в реальном времени.

## Решения

| Вопрос | Решение | Почему |
|--------|---------|--------|
| Подтверждение оплаты | Trust-based | Проект для портфолио, не требует API банка |
| Стек | Python + aiogram 3 | Самый зрелый фреймворк для TG-ботов |
| База данных | SQLite + aiosqlite | Zero-dependency, запуск без docker-compose с БД |
| Карточка | Pillow-картинка + inline-кнопки | Полный контроль дизайна + интерактивность |
| Деплой | Docker one-liner | Один способ = минимум когнитивной нагрузки |
| Реквизиты | Онбординг в ЛС + переопределение в inline | Гибкость без усложнения |
| Архитектура | Layered monolith | Чистые слои в одном процессе |

## Структура проекта

```
tgpay/
├── bot/
│   ├── __init__.py
│   ├── __main__.py              # python -m bot
│   ├── config.py                # pydantic-settings (BaseSettings)
│   ├── app.py                   # создаёт Dispatcher, подключает routers
│   ├── routers/
│   │   ├── __init__.py          # агрегирует все routers
│   │   ├── inline.py            # inline_query + chosen_inline_result
│   │   ├── callbacks.py         # CallbackData хэндлеры (оплатил/отмена)
│   │   └── private.py           # ЛС: /start, онбординг через FSM
│   ├── services/
│   │   ├── __init__.py
│   │   ├── payment.py           # бизнес-логика платежей
│   │   ├── card_renderer.py     # Pillow: генерация карточки + QR
│   │   └── sbp.py               # формирование СБП deeplink
│   ├── db/
│   │   ├── __init__.py
│   │   ├── engine.py            # aiosqlite engine + session factory
│   │   ├── models.py            # User, Payment, PaymentParticipant
│   │   └── repositories.py     # async CRUD
│   ├── middlewares.py           # DbSessionMiddleware
│   ├── keyboards.py             # InlineKeyboardBuilder фабрики
│   ├── callback_data.py         # PaymentAction(CallbackData)
│   ├── states.py                # OnboardingStates(StatesGroup)
│   └── enums.py                 # перечисления
├── assets/
│   ├── fonts/
│   │   └── Inter-Bold.ttf
│   └── card_bg.png
├── tests/
│   ├── conftest.py
│   ├── test_payment_service.py
│   └── test_card_renderer.py
├── Dockerfile
├── pyproject.toml
├── .env.example
└── README.md
```

Принцип: routers → services → repositories → db. Слои не пересекаются.

## Модели данных

```python
class Base(AsyncAttrs, DeclarativeBase):
    pass

class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

class User(TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str | None]
    first_name: Mapped[str]
    phone: Mapped[str | None]           # +7... для СБП
    bank_name: Mapped[str | None]       # "sber", "tinkoff"
    is_onboarded: Mapped[bool] = mapped_column(default=False)

    created_payments: Mapped[list["Payment"]] = relationship(
        back_populates="creator", foreign_keys="Payment.creator_id"
    )

class Payment(TimestampMixin, Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    creator_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"))
    amount: Mapped[int]                    # копейки, 50000 = 500₽
    description: Mapped[str]
    inline_message_id: Mapped[str | None] = mapped_column(index=True)
    card_file_id: Mapped[str | None]

    creator: Mapped["User"] = relationship(foreign_keys=[creator_id])
    participants: Mapped[list["PaymentParticipant"]] = relationship(
        back_populates="payment", lazy="selectin"
    )

class PaymentParticipant(TimestampMixin, Base):
    __tablename__ = "payment_participants"

    payment_id: Mapped[int] = mapped_column(ForeignKey("payments.id"), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.telegram_id"), primary_key=True)

    payment: Mapped["Payment"] = relationship(back_populates="participants")
    user: Mapped["User"] = relationship()
```

## User Flow

### 1. Онбординг (один раз, в ЛС)

```
Юзер → /start → "Введи номер телефона для СБП"
     → +79991234567 → FSM: OnboardingStates.phone
     → "Выбери банк" → [Сбер] [Т-Банк] [Альфа] ...
     → выбирает → is_onboarded = True
     → "Готово! Используй @TGpayBot в любом чате"
```

### 2. Создание платежа (inline)

```
@TGpayBot 500 за ужин
        ↓
inline_query: парсим amount=50000, description="за ужин"
        ↓
Не онборжен? → кнопка "Настроить бота" (switch_pm)
Онборжен?    → показываем превью
        ↓
chosen_inline_result:
  - card_renderer генерирует картинку
  - sbp.py формирует deeplink
  - сохраняем Payment в БД
  - запоминаем inline_message_id
        ↓
В чате: [Карточка с QR] + кнопки [Оплатить по СБП] [Я оплатил]
```

### 3. Подтверждение оплаты (trust-based)

```
Кто-то нажимает "Я оплатил"
        ↓
Уже в participants? → игнор
Нет → INSERT PaymentParticipant
        ↓
Перегенерировать карточку с обновлённым списком
edit_message_media(inline_message_id=...)
        ↓
Карточка обновляется: добавляется "✓ @username"
```

## Генерация карточки

Два визуальных состояния:

```
┌─────────────────────────────┐    ┌─────────────────────────────┐
│  ░░░ тёмный фон / градиент  │    │  ░░░ тёмный фон / градиент  │
│                             │    │                             │
│        500 ₽               │    │        500 ₽               │
│     за ужин                │    │     за ужин                │
│                             │    │                             │
│      ┌─────────┐           │    │      ┌─────────┐           │
│      │ QR-код  │           │    │      │ QR-код  │           │
│      │  СБП    │           │    │      │  СБП    │           │
│      └─────────┘           │    │      └─────────┘           │
│                             │    │                             │
│                             │    │  ✓ @alice  ✓ @bob          │
│                             │    │                             │
│   @creator • TGpay         │    │   @creator • TGpay         │
└─────────────────────────────┘    └─────────────────────────────┘
     Никто не оплатил                  Есть оплатившие
```

- Pillow: рисуем на Image.new() или фоновом шаблоне
- qrcode: генерация QR с СБП deeplink
- Шрифт Inter (Google Fonts, open-source)
- Возвращаем BytesIO → BufferedInputFile

## Пайплайн агентов

### Роли

| Роль | Задача | Сессия |
|------|--------|--------|
| Архитектор | Дизайн, план, решения | Сессия 1 |
| Исполнитель | Код по плану | Сессии 2, 3, ... |
| Ревьюер | Ревью PR | По необходимости |

### Передача контекста

```
docs/
├── plans/
│   ├── 2026-03-07-tgpay-design.md   ← Архитектор (markdown, для GitHub)
│   └── PLAN.json                     ← Архитектор (JSON, для агентов)
CLAUDE.md                             ← Конвенции, auto-loaded
```

### Пайплайн

```
АРХИТЕКТОР → design.md + PLAN.json + CLAUDE.md → коммит в main
        ↓
ИСПОЛНИТЕЛЬ → читает PLAN.json → берёт pending шаг → ветка → код + тесты → PR
        ↓
РЕВЬЮЕР → читает PR → проверяет по design.md → комментарии / approve
        ↓
ИСПОЛНИТЕЛЬ → фиксит замечания → мержит → следующий шаг
```

## GitHub-стратегия

### README.md
- Hero-картинка с карточкой
- GIF-демо (10 секунд)
- One-liner запуск (docker run)
- Секция архитектуры
- "Собран с помощью AI" + ссылка на docs/plans/

### CI
- ruff check + ruff format
- mypy
- pytest
- docker build

### Бонусы
- Topic tags: telegram-bot, sbp, payment, aiogram, python
- Social preview image
- Releases с changelog
- MIT лицензия

Всё описание на русском (СБП работает только в РФ).
