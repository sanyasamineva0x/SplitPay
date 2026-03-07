# TGpay

> Inline Telegram-бот для мгновенных запросов на оплату через СБП

**Статус:** в разработке

## Что это

Пишешь `@TGpayBot 500 за ужин` в любом чате — бот генерирует стильную карточку с QR-кодом СБП. Любой участник чата нажимает "Я оплатил" — карточка обновляется в реальном времени.

## Стек

Python 3.12 · aiogram 3 · SQLAlchemy 2.0 · Pillow · aiosqlite

## Архитектура

```
routers/ → services/ → repositories/ → SQLite
              ↘ card_renderer (Pillow + QR)
```

Layered monolith: чистые слои, один Docker-контейнер.

## Разработка

```bash
pip install -e ".[dev]"
pytest tests/ -v
ruff check bot/ tests/
```

## Собран с помощью AI

Проект спроектирован, реализован и отревьюирован мультиагентным пайплайном Claude Code.
Весь процесс — в [docs/plans/](docs/plans/).
