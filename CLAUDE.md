# SplitPay

Inline Telegram-бот для разделения расходов между друзьями.

## Стек
- Python 3.12, aiogram 3, SQLAlchemy 2.0 async, aiosqlite, Pillow
- pydantic-settings для конфигурации
- pytest + pytest-asyncio для тестов
- ruff для линтинга и форматирования

## Архитектура
Layered monolith: `bot/routers/` → `bot/services/` → `bot/db/repositories.py` → SQLite.
Слои не пересекаются. Handlers не обращаются к БД напрямую.

## Документы
- Дизайн: `docs/plans/2026-03-08-splitpay-design.md`
- Implementation plan: `docs/plans/2026-03-08-implementation.md`
- Прогресс: `docs/plans/PLAN.json`
- Промпты агентов: `docs/plans/PROMPTS.md`

## Конвенции
- Язык кода: Python, комментарии и строки на русском
- Форматтер: `ruff format`
- Линтер: `ruff check`
- Тесты: pytest, async тесты через pytest-asyncio
- amount всегда в копейках (int), 50000 = 500₽
- Коммиты на русском: `feat: описание`, `fix: описание`
- TDD: сначала тест, потом реализация
- Один шаг из PLAN.json = одна ветка = один PR

## Команды
```bash
pip install -e ".[dev]"        # установка
pytest tests/ -v               # тесты
ruff check bot/ tests/         # линт
ruff format bot/ tests/        # формат
docker-compose up -d           # запуск через Docker
python -m bot                  # запуск (нужен .env с BOT_TOKEN)
```

## Мультиагентный пайплайн
- **Исполнитель**: читает PLAN.json → берёт первый `pending` шаг → ветка → код + тесты → PR → ставит `done` в PLAN.json
- **Ревьюер**: читает PR → проверяет по design.md → approve/комментарии
