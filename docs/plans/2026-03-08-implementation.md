# SplitPay — План реализации

> Пошаговый план переделки TGpay → SplitPay.
> Каждый шаг = одна ветка = один PR.
> TDD: сначала тесты, потом реализация.

## Обзор

Переделываем TGpay (inline-бот для СБП-запросов) в SplitPay (inline-бот
для разделения расходов). Переиспользуем ~60% кода: архитектуру, middleware,
онбординг, CI, Docker. Убираем СБП/QR, добавляем split-логику.

**Дизайн-документ**: `docs/plans/2026-03-08-splitpay-design.md`
**Прогресс**: `docs/plans/PLAN.json`

---

## Шаг 1. Удаление старого кода

**Ветка**: `feat/cleanup-old-code`

Удаляем всё, что связано с СБП, QR-кодами и старой платёжной логикой.

**Удалить файлы:**
- `bot/services/sbp.py` — генерация СБП-ссылок
- `bot/services/payment.py` — старый сервис платежей
- `tests/test_sbp.py` — тесты СБП
- `tests/test_payment_service.py` — тесты платежей

**Изменить файлы:**
- `pyproject.toml` — убрать `qrcode[pil]` из зависимостей
- `bot/db/models.py` — убрать модели `Payment`, `PaymentParticipant`
- `bot/db/repositories.py` — убрать `PaymentRepo`
- `bot/services/card_renderer.py` — убрать QR-логику, оставить заглушку
- `bot/routers/inline.py` — убрать импорты payment/sbp, оставить заглушку
- `bot/routers/callbacks.py` — убрать импорты payment, оставить заглушку
- `bot/callback_data.py` — убрать `PaymentCallback`

**Критерии приёмки:**
- `qrcode` отсутствует в pyproject.toml
- `ruff check bot/` — без ошибок
- `pip install -e '.[dev]'` — без ошибок

---

## Шаг 2. Переименование TGpay → SplitPay

**Ветка**: `feat/rename-splitpay`
**Зависит от**: шаг 1

Меняем название проекта во всех файлах. Внутренний пакет `bot/` не
переименовываем — это деталь реализации.

**Файлы:**
- `pyproject.toml` — name = "splitpay", description
- `bot/config.py` — database_url default: splitpay.db
- `.env.example` — комментарии
- `bot/routers/private.py` — тексты бота (@SplitPayBot)
- `bot/services/card_renderer.py` — футер, placeholder
- `README.md` — название и описание
- `CLAUDE.md` — название и описание
- `Dockerfile` — комментарии
- `.github/workflows/ci.yml` — название workflow

**Критерии приёмки:**
- `grep -r 'TGpay' bot/` — пусто
- `grep 'splitpay' pyproject.toml` — найдено

---

## Шаг 3. Новые модели: Expense, ExpenseParticipant

**Ветка**: `feat/expense-models`
**Зависит от**: шаг 1

Создаём новые модели для расходов. Ключевое отличие от старых:
`ExpenseParticipant` хранит **долю** (`amount`) и **статус погашения**
(`is_settled`, `settled_at`).

**Модели:**

```python
class Expense:
    id: int                 # PK, autoincrement
    creator_id: int         # FK → User (кто заплатил)
    amount: int             # сумма в копейках
    description: str        # "за ужин"
    inline_message_id: str | None  # indexed
    card_file_id: str | None
    created_at: datetime
    participants: list[ExpenseParticipant]

class ExpenseParticipant:
    expense_id: int         # FK → Expense, PK
    user_id: int            # FK → User, PK
    amount: int             # доля в копейках
    is_settled: bool        # отдал или нет (default False)
    settled_at: datetime | None
```

**Тесты (TDD — сначала тесты):**
- `test_create_expense` — создание расхода
- `test_create_expense_with_participants` — расход с участниками
- `test_participant_settled` — отметка погашения

**Критерии приёмки:**
- `pytest tests/test_models.py -v` — 3+ PASSED

---

## Шаг 4. Репозиторий ExpenseRepo

**Ветка**: `feat/expense-repo`
**Зависит от**: шаг 3

CRUD-операции для расходов.

**Методы:**
- `create(session, creator_id, amount, description) → Expense`
- `get_by_id(session, expense_id) → Expense | None`
- `set_inline_message_id(session, expense_id, inline_message_id)`
- `set_card_file_id(session, expense_id, file_id)`
- `add_participant(session, expense_id, user_id, amount) → bool`
- `settle_participant(session, expense_id, user_id) → bool`

**Тесты (TDD):**
- `test_expense_create`
- `test_expense_get_by_id`
- `test_expense_add_participant`
- `test_expense_add_participant_duplicate`
- `test_expense_settle_participant`

**Критерии приёмки:**
- `pytest tests/test_repositories.py -v` — 8+ PASSED (3 UserRepo + 5 ExpenseRepo)

---

## Шаг 5. Адаптация card_renderer.py

**Ветка**: `feat/new-card-design`
**Зависит от**: шаг 2

Новый дизайн карточки. Убираем QR-код, добавляем реквизиты и список
должников.

**Элементы карточки:**
- Сумма (крупно, по центру)
- Описание
- Блок реквизитов: "Перевести: @username / Банк: Сбер / +7 999 123 45 67"
- Список участников: "○ @vasya — 750 ₽" или "✓ @vasya — отдал"

**Сигнатура:**
```python
def render_card(
    amount: int,
    description: str,
    creator_name: str,
    bank_name: str | None,
    phone: str | None,
    participants: list[dict],  # {name, amount, is_settled}
) -> BytesIO
```

**Также**: новый `ExpenseCallback` в `callback_data.py`:
```python
class ExpenseCallback(CallbackData, prefix="exp"):
    expense_id: int
    action: str  # "join" | "settle"
```

**Тесты (TDD):**
- `test_render_card_no_participants`
- `test_render_card_with_settled_and_unsettled`
- `test_render_card_shows_bank_details`
- `test_render_placeholder`

**Критерии приёмки:**
- `pytest tests/test_card_renderer.py -v` — 4+ PASSED

---

## Шаг 6. Сервис expense_service.py

**Ветка**: `feat/expense-service`
**Зависит от**: шаги 4, 5

Бизнес-логика разделения расходов.

**Методы:**
- `create_expense(session, creator_id, amount, description) → (Expense, BytesIO)`
  Создаёт расход, рендерит начальную карточку (без участников).

- `join_expense(session, expense_id, user_id) → JoinResult`
  Добавляет участника-должника. Пересчитывает доли всех участников:
  `amount / (число_участников)`. Создатель не входит в должники.

- `settle_debt(session, expense_id, user_id) → SettleResult`
  Отмечает участника как отдавшего. Перерисовывает карточку.

**Логика split:**
Равные доли. Сумма делится на количество участников (без создателя).
Пример: 3000₽, 3 участника → по 1000₽ каждому.
При добавлении нового участника доли пересчитываются.

**Тесты (TDD):**
- `test_create_expense`
- `test_join_expense_splits_equally`
- `test_join_multiple_recalculates`
- `test_settle_debt`
- `test_settle_debt_duplicate`
- `test_settle_debt_creator_cannot`

**Критерии приёмки:**
- `pytest tests/test_expense_service.py -v` — 6+ PASSED

---

## Шаг 7. Переписать inline handler

**Ветка**: `feat/inline-expense`
**Зависит от**: шаг 6

Inline query для создания расходов.

**Флоу:**
1. Пользователь пишет `@SplitPayBot 3000 за ужин`
2. `on_inline_query` парсит сумму и описание
3. Если не онборден — показывает "Сначала настрой бота"
4. Показывает inline result с placeholder
5. `on_chosen_result` создаёт Expense, рендерит карточку
6. Отправляет карточку с кнопками: "Я должен" + "Я отдал ✓"

**Кнопки:**
- "Я должен 💰" → `ExpenseCallback(expense_id=X, action="join")`
- "Я отдал ✓" → `ExpenseCallback(expense_id=X, action="settle")`

**Критерии приёмки:**
- `python -c 'from bot.routers.inline import router'` — без ошибок
- `ruff check bot/routers/inline.py` — без ошибок

---

## Шаг 8. Переписать callback handler

**Ветка**: `feat/callbacks-expense`
**Зависит от**: шаг 6

Обработка нажатий на кнопки карточки.

**action="join":**
1. Проверить: не создатель ли нажал (создатель не может быть должником)
2. Проверить: не участник ли уже
3. Добавить через `ExpenseService.join_expense`
4. Обновить карточку (новый PNG с пересчитанными долями)

**action="settle":**
1. Проверить: участник ли нажал
2. Проверить: не отдал ли уже
3. Отметить через `ExpenseService.settle_debt`
4. Обновить карточку

**Критерии приёмки:**
- `python -c 'from bot.routers.callbacks import router'` — без ошибок
- `ruff check bot/routers/callbacks.py` — без ошибок

---

## Шаг 9. Обновить онбординг

**Ветка**: `feat/onboarding-texts`
**Зависит от**: шаг 2

Обновить тексты в `bot/routers/private.py`:
- Приветствие: "Привет! Я помогу разделить расходы с друзьями."
- Инструкция: "Введи номер телефона, чтобы друзья знали куда переводить"
- Финал: "Готово! В любом чате: @SplitPayBot 500 за кофе"
- Убрать упоминания СБП

**Критерии приёмки:**
- `grep 'SplitPayBot' bot/routers/private.py` — найдено
- `grep 'TGpayBot' bot/routers/private.py` — пусто

---

## Шаг 10. docker-compose.yml

**Ветка**: `feat/docker-compose`
**Зависит от**: шаг 2

```yaml
services:
  bot:
    build: .
    env_file: .env
    volumes:
      - ./data:/app/data
    restart: unless-stopped
```

Обновить `bot/config.py`: default database_url →
`sqlite+aiosqlite:///data/splitpay.db` (чтобы БД лежала в volume).

**Критерии приёмки:**
- `docker-compose config` — валидный YAML
- `docker build -t splitpay .` — успешно

---

## Шаг 11. Railway deploy config

**Ветка**: `feat/railway-deploy`
**Зависит от**: шаг 10

Файлы для one-click deploy на Railway:

**railway.json:**
```json
{
  "$schema": "https://railway.app/railway.schema.json",
  "build": {"builder": "DOCKERFILE"},
  "deploy": {"startCommand": "python -m bot"}
}
```

**Procfile:**
```
worker: python -m bot
```

**Критерии приёмки:**
- `railway.json` — валидный JSON
- `Procfile` содержит `worker: python -m bot`

---

## Шаг 12. Обновить README

**Ветка**: `feat/readme-update`
**Зависит от**: шаги 7, 8, 9, 10, 11

Полностью переписать README.md:
- Название и описание SplitPay
- Возможности (split, карточки, реквизиты)
- Быстрый старт: Docker Compose + Railway (кнопка Deploy)
- Стек (без qrcode)
- Архитектура
- Примеры: `@SplitPayBot 3000 за ужин`
- Лицензия

**Критерии приёмки:**
- `grep 'SplitPay' README.md` — найдено
- `grep 'docker-compose' README.md` — найдено
- `grep 'Railway' README.md` — найдено

---

## Шаг 13. CLAUDE.md и финальная проверка

**Ветка**: `feat/claude-md-final`
**Зависит от**: шаг 12

Обновить CLAUDE.md:
- Название: SplitPay
- Описание: inline Telegram-бот для разделения расходов
- Стек: без qrcode
- Ссылки на новые доки
- Команды (splitpay вместо tgpay)

Финальная проверка:
- `ruff check bot/ tests/` — без ошибок
- `ruff format --check bot/ tests/` — без ошибок
- `pytest tests/ -v` — все тесты проходят
- `docker build -t splitpay .` — успешно

---

## Граф зависимостей

```
1 (cleanup) ──┬──→ 2 (rename) ──┬──→ 5 (card) ──┐
              │                 ├──→ 9 (onboard) │
              │                 └──→ 10 (docker) → 11 (railway)
              │                                  │
              └──→ 3 (models) → 4 (repo) ────────┤
                                                 │
                                     5 + 4 ──→ 6 (service) ──┬→ 7 (inline)
                                                              └→ 8 (callbacks)
                                                                    │
                                              7 + 8 + 9 + 10 + 11 → 12 (readme) → 13 (final)
```
