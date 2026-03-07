# TGpay

> Inline Telegram-бот для мгновенных запросов на оплату через СБП

## Что это

Пишешь `@TGpayBot 500 за ужин` в любом чате — бот генерирует стильную карточку с QR-кодом СБП. Любой участник чата нажимает «Я оплатил» — карточка обновляется в реальном времени.

## Возможности

- **Inline-режим** — работает в любом чате без добавления бота
- **Карточка оплаты** — PNG с суммой, описанием, QR-кодом и списком оплативших
- **СБП deeplink** — QR-код ведёт прямо в приложение банка (Сбер, Т-Банк, Альфа, ВТБ, Райффайзен)
- **Онбординг** — /start → ввод телефона → выбор банка → готов
- **Обновление в реальном времени** — карточка перерисовывается при каждой новой оплате

## Быстрый старт

```bash
docker run -e BOT_TOKEN=your_token ghcr.io/sanyasamineva0x/tgpay
```

Или локально:

```bash
git clone https://github.com/sanyasamineva0x/TGpay.git
cd TGpay
cp .env.example .env  # заполнить BOT_TOKEN
pip install -e .
python -m bot
```

## Стек

Python 3.12 · aiogram 3 · SQLAlchemy 2.0 · Pillow · qrcode · aiosqlite · pydantic-settings

## Архитектура

```
bot/routers/     →  bot/services/     →  bot/db/repositories.py  →  SQLite
  private.py           payment.py            UserRepo
  inline.py            card_renderer.py      PaymentRepo
  callbacks.py         sbp.py
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
