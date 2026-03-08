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

## Шаг 1. Удаление старого кода ✅

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

## Шаг 2. Переименование TGpay → SplitPay + тексты

**Ветка**: `feat/rename-splitpay`
**Зависит от**: шаг 1

Меняем название проекта и все пользовательские тексты. Внутренний пакет
`bot/` не переименовываем — это деталь реализации.

**Файлы:**
- `pyproject.toml` — name = "splitpay", description
- `bot/config.py` — database_url default: splitpay.db
- `.env.example` — комментарии
- `bot/routers/private.py` — все тексты онбординга:
  - Приветствие: "Привет! Я помогу разделить расходы с друзьями."
  - Инструкция: "Введи номер телефона, чтобы друзья знали куда переводить"
  - Финал: "Готово! В любом чате: @SplitPayBot 500 за кофе"
  - Убрать упоминания СБП
- `bot/services/card_renderer.py` — футер, placeholder
- `README.md` — название и описание (минимально, полная переделка в шаге 11)
- `CLAUDE.md` — название, описание, стек, ссылки на новые доки
- `Dockerfile` — комментарии
- `.github/workflows/ci.yml` — название workflow

**Критерии приёмки:**
- `grep -r 'TGpay' bot/` — пусто
- `grep -r 'TGpayBot' bot/` — пусто
- `grep 'splitpay' pyproject.toml` — найдено
- `grep 'SplitPayBot' bot/routers/private.py` — найдено

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

**Также**: новый `ExpenseCallback` в `callback_data.py`:
```python
class ExpenseCallback(CallbackData, prefix="exp"):
    expense_id: int
    action: str  # "join" | "settle"
```

**Тесты (TDD — сначала тесты):**
- `test_create_expense` — создание расхода
- `test_create_expense_with_participants` — расход с участниками и долями
- `test_participant_settled` — отметка погашения, проверка settled_at

**Критерии приёмки:**
- `pytest tests/test_models.py -v` — 3+ PASSED
- `python -c 'from bot.callback_data import ExpenseCallback'` — без ошибок

---

## Шаг 4. Репозиторий ExpenseRepo

**Ветка**: `feat/expense-repo`
**Зависит от**: шаг 3

CRUD-операции для расходов.

**Методы:**
- `create(session, creator_id, amount, description) → Expense`
- `get_by_id(session, expense_id) → Expense | None`
  - Загружает с participants + user relationships (joinedload)
- `set_inline_message_id(session, expense_id, inline_message_id)`
- `set_card_file_id(session, expense_id, file_id)`
- `add_participant(session, expense_id, user_id, amount) → bool`
  - Возвращает False если уже участник (дубликат)
- `settle_participant(session, expense_id, user_id) → bool`
  - Возвращает False если не участник или уже settled
- `update_participant_amounts(session, expense_id, new_amount) → None`
  - Обновляет amount у всех несеттленных участников (при пересчёте долей)

**Тесты (TDD):**
- `test_expense_create`
- `test_expense_get_by_id`
- `test_expense_add_participant`
- `test_expense_add_participant_duplicate` — возвращает False
- `test_expense_settle_participant`
- `test_expense_settle_not_participant` — возвращает False
- `test_expense_update_amounts`

**Критерии приёмки:**
- `pytest tests/test_repositories.py -v` — 10+ PASSED (3 UserRepo + 7 ExpenseRepo)

---

## Шаг 5. Адаптация card_renderer.py (новый дизайн)

**Ветка**: `feat/new-card-design`
**Зависит от**: шаг 2

Новый дизайн карточки. Без QR-кода, с реквизитами и списком должников.

**Элементы карточки:**
- Сумма (крупно, по центру)
- Описание
- Блок реквизитов: "Перевести: @username / Банк: Сбер / +7 999 123 45 67"
- Если есть участники: список с иконками (○ / ✓) и суммой
- Если нет участников: "Нажмите «Я должен», чтобы разделить счёт"

**Сигнатура:**
```python
def render_card(
    amount: int,
    description: str,
    creator_name: str,
    bank_name: str | None,
    phone: str | None,
    participants: list[dict],  # [{name, amount, is_settled}]
) -> BytesIO
```

**Тесты (TDD):**
- `test_render_card_no_participants` — карточка без участников
- `test_render_card_with_participants` — с settled и unsettled
- `test_render_card_shows_bank_details` — банк и телефон на карточке
- `test_render_placeholder` — placeholder с текстом SplitPay

**Критерии приёмки:**
- `pytest tests/test_card_renderer.py -v` — 4+ PASSED

---

## Шаг 6. Сервис expense_service.py (split-логика)

**Ветка**: `feat/expense-service`
**Зависит от**: шаги 4, 5

Бизнес-логика разделения расходов.

**Методы:**
- `create_expense(session, creator_id, amount, description) → (Expense, BytesIO)`
  Создаёт расход, рендерит начальную карточку (без участников).

- `join_expense(session, expense_id, user_id) → JoinResult`
  Добавляет участника-должника. Пересчитывает доли **всех** участников:
  `total_amount / число_участников` (создатель НЕ входит в должники).
  Остаток от деления добавляется первому участнику.
  Возвращает обновлённую карточку.

- `settle_debt(session, expense_id, user_id) → SettleResult`
  Отмечает участника как отдавшего. Перерисовывает карточку.

**Логика split (равные доли):**
- Сумма делится на количество участников (без создателя)
- Деление в копейках нацело: `amount_per_person = total // count`
- Остаток: `remainder = total % count`
- Первый участник получает `amount_per_person + remainder`
- Пример: 1000₽ / 3 → 333.34₽ + 333.33₽ + 333.33₽

**Валидация:**
- Сумма: от 100 до 100_000_000 копеек (1₽ — 1 000 000₽)
- Описание: 1-100 символов
- Создатель не может join свой расход
- Создатель не может settle (ему должны, а не он)

**Тесты (TDD):**
- `test_create_expense` — создание расхода и начальная карточка
- `test_join_expense_splits_equally` — 1000 / 2 = 500 + 500
- `test_join_expense_with_remainder` — 1000 / 3 = 334 + 333 + 333
- `test_join_multiple_recalculates` — доли пересчитываются при join
- `test_settle_debt` — отметка погашения
- `test_settle_debt_duplicate` — повторный settle → ошибка
- `test_join_creator_cannot` — создатель не может join
- `test_settle_creator_cannot` — создатель не может settle
- `test_validate_amount_min_max` — проверка границ суммы

**Критерии приёмки:**
- `pytest tests/test_expense_service.py -v` — 9+ PASSED

---

## Шаг 7. Переписать inline handler

**Ветка**: `feat/inline-expense`
**Зависит от**: шаг 6

Inline query для создания расходов.

**Флоу:**
1. Пользователь пишет `@SplitPayBot 3000 за ужин`
2. `on_inline_query` парсит сумму и описание
3. Если не онборден — показывает "Сначала настрой бота"
4. Если сумма невалидна — показывает подсказку формата
5. Показывает inline result с placeholder
6. `on_chosen_result` создаёт Expense, рендерит карточку
7. Отправляет карточку с кнопками: "Я должен 💰" + "Я отдал ✓"

**Парсинг:**
- `"3000 за ужин"` → amount=300000, description="за ужин"
- `"500.50 кофе"` → amount=50050, description="кофе"
- `"abc"` → ошибка, показать подсказку

**Кнопки:**
- "Я должен 💰" → `ExpenseCallback(expense_id=X, action="join")`
- "Я отдал ✓" → `ExpenseCallback(expense_id=X, action="settle")`

**Тесты:**
- `test_parse_inline_query_valid` — парсинг суммы и описания
- `test_parse_inline_query_decimal` — парсинг дробных сумм
- `test_parse_inline_query_invalid` — невалидный ввод
- `test_parse_inline_query_no_description` — сумма без описания

**Критерии приёмки:**
- `pytest tests/test_inline.py -v` — 4+ PASSED
- `ruff check bot/routers/inline.py` — без ошибок

---

## Шаг 8. Переписать callback handler

**Ветка**: `feat/callbacks-expense`
**Зависит от**: шаг 6

Обработка нажатий на кнопки карточки.

**action="join":**
1. Проверить: не создатель ли нажал → answer "Вы создатель этого расхода"
2. Проверить: не участник ли уже → answer "Вы уже в списке"
3. Добавить через `ExpenseService.join_expense`
4. Обновить карточку (новый PNG с пересчитанными долями)

**action="settle":**
1. Проверить: участник ли нажал → answer "Вы не в списке должников"
2. Проверить: не отдал ли уже → answer "Вы уже отметили оплату"
3. Отметить через `ExpenseService.settle_debt`
4. Обновить карточку

**Обновление карточки:**
Используем тот же workaround из TGpay:
send_photo → получить file_id → delete → edit_message_media с file_id.
(Inline messages не поддерживают загрузку новых файлов.)

**Тесты:**
- `test_callback_join_success`
- `test_callback_join_creator_rejected`
- `test_callback_join_duplicate_rejected`
- `test_callback_settle_success`
- `test_callback_settle_not_participant`

**Критерии приёмки:**
- `pytest tests/test_callbacks.py -v` — 5+ PASSED
- `ruff check bot/routers/callbacks.py` — без ошибок

---

## Шаг 9. docker-compose.yml

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

## Шаг 10. Railway deploy config

**Ветка**: `feat/railway-deploy`
**Зависит от**: шаг 9

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

## Шаг 11. Обновить README

**Ветка**: `feat/readme-update`
**Зависит от**: шаги 7, 8, 9, 10

Полностью переписать README.md:
- Название и описание SplitPay
- Скриншот/мокап карточки
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

## Шаг 12. Финальная проверка

**Ветка**: `feat/final-check`
**Зависит от**: шаг 11

Финальная проверка всего проекта:
- `ruff check bot/ tests/` — без ошибок
- `ruff format --check bot/ tests/` — без ошибок
- `pytest tests/ -v` — все тесты проходят
- `docker build -t splitpay .` — успешно
- Ручной тест: запустить бота, отправить inline query, проверить карточку

---

## Граф зависимостей

```
1 (cleanup) ──┬──→ 2 (rename + тексты) ──┬──→ 5 (card) ──┐
              │                           └──→ 9 (docker) → 10 (railway)
              │                                            │
              └──→ 3 (models + callback_data) → 4 (repo) ─┤
                                                           │
                                               5 + 4 ──→ 6 (service) ──┬→ 7 (inline)
                                                                        └→ 8 (callbacks)
                                                                              │
                                                    7 + 8 + 9 + 10 ──→ 11 (readme) → 12 (final)
```

## Итого: 12 шагов (было 13)

Объединено:
- Шаг 2 + старый шаг 9 (онбординг) → единый "Переименование + тексты"
- Шаг 3 + ExpenseCallback → модели + callback_data в одном шаге
- Старый шаг 13 (CLAUDE.md) → поглощён шагом 2 (rename)
