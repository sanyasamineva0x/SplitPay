# SplitPay

> Inline Telegram-бот для разделения расходов между друзьями

## Что это

Пишешь `@SplitPayBot 3000 за ужин` в любом чате — бот создаёт карточку с суммой и реквизитами. Участники нажимают «Я должен» — бот пересчитывает доли. После перевода отмечают «Я отдал» — карточка обновляется.

## Возможности

- **Inline-режим** — работает в любом чате без добавления бота
- **Автоматический split** — сумма делится поровну между участниками
- **Динамические доли** — каждый новый участник пересчитывает суммы
- **Карточка расхода** — PNG с суммой, реквизитами и списком должников
- **Онбординг** — /start → ввод телефона → выбор банка → готов

## Быстрый старт

```bash
git clone https://github.com/sanyasamineva0x/SplitPay.git
cd SplitPay
cp .env.example .env  # заполнить BOT_TOKEN
pip install -e .
python -m bot
```

## Стек

Python 3.12 · aiogram 3 · SQLAlchemy 2.0 · Pillow · aiosqlite · pydantic-settings

## Архитектура

```
bot/routers/     →  bot/services/     →  bot/db/repositories.py  →  SQLite
  private.py           card_renderer.py      UserRepo
  inline.py            expense_service.py    ExpenseRepo
  callbacks.py
```

Layered monolith: чистые слои, один Docker-контейнер.

## Разработка

```bash
pip install -e ".[dev]"     # установка с dev-зависимостями
pytest tests/ -v            # тесты
ruff check bot/ tests/      # линт
ruff format bot/ tests/     # форматирование
python -m bot               # запуск (нужен .env с BOT_TOKEN)
```

## Собран с помощью AI

Проект спроектирован, реализован и отревьюирован мультиагентным пайплайном Claude Code.
Весь процесс — в [docs/plans/](docs/plans/).

## Лицензия

MIT
