from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "Inter-Bold.ttf"

# Размеры карточки
CARD_WIDTH = 600
CARD_PADDING = 40
INNER_WIDTH = CARD_WIDTH - CARD_PADDING * 2

# Цвета — минималистичный светлый стиль
BG_COLOR = "#ffffff"
TEXT_PRIMARY = "#1a1a1a"
TEXT_SECONDARY = "#6b7280"
ACCENT_COLOR = "#2563eb"
PAID_COLOR = "#16a34a"
UNPAID_COLOR = "#dc2626"
DIVIDER_COLOR = "#e5e7eb"


@dataclass
class Participant:
    name: str  # @username или first_name
    amount: int  # доля в копейках
    is_settled: bool


def _format_amount(kopecks: int) -> str:
    """Форматирование суммы в копейках → строка в рублях."""
    rubles = kopecks // 100
    kop = kopecks % 100
    if kop:
        return f"{rubles},{kop:02d} ₽"
    return f"{rubles:,} ₽".replace(",", " ")


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    try:
        return ImageFont.truetype(str(FONT_PATH), size)
    except OSError:
        return ImageFont.load_default()


def render_card(
    amount: int,
    description: str,
    creator_name: str,
    bank_label: str,
    phone: str,
    participants: list[Participant],
) -> BytesIO:
    """Генерация карточки расхода — минималистичный светлый стиль."""
    font_amount = _load_font(48)
    font_desc = _load_font(20)
    font_label = _load_font(15)
    font_participant = _load_font(16)
    font_footer = _load_font(14)
    font_hint = _load_font(14)

    # Расчёт высоты карточки (динамическая)
    y = CARD_PADDING
    y += 56  # сумма
    y += 10  # отступ
    y += 28  # описание
    y += 20  # отступ до разделителя
    y += 1  # разделитель
    y += 16  # отступ
    y += 20  # "Заплатил:" заголовок
    y += 4  # отступ
    y += 20  # реквизиты (банк + телефон)
    y += 20  # отступ

    if participants:
        y += 1  # разделитель
        y += 16  # отступ
        y += 20  # заголовок "Должны:"
        y += 8  # отступ
        y += len(participants) * 28  # участники
        y += 16  # отступ
    else:
        y += 1  # разделитель
        y += 16  # отступ
        y += 20  # подсказка строка 1
        y += 4
        y += 20  # подсказка строка 2
        y += 16  # отступ

    y += 1  # разделитель футера
    y += 12  # отступ
    y += 20  # футер
    y += CARD_PADDING

    card_height = y

    img = Image.new("RGBA", (CARD_WIDTH, card_height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    y = CARD_PADDING

    # Сумма — крупно, по центру
    amount_text = _format_amount(amount)
    bbox = draw.textbbox((0, 0), amount_text, font=font_amount)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, y),
        amount_text,
        fill=TEXT_PRIMARY,
        font=font_amount,
    )
    y += 56

    # Описание — серым, по центру
    y += 10
    bbox = draw.textbbox((0, 0), description, font=font_desc)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, y),
        description,
        fill=TEXT_SECONDARY,
        font=font_desc,
    )
    y += 28

    # Разделитель
    y += 20
    draw.line(
        [(CARD_PADDING, y), (CARD_WIDTH - CARD_PADDING, y)],
        fill=DIVIDER_COLOR,
        width=1,
    )
    y += 1

    # Реквизиты создателя
    y += 16
    draw.text(
        (CARD_PADDING, y),
        f"Заплатил: {creator_name}",
        fill=TEXT_PRIMARY,
        font=font_label,
    )
    y += 20 + 4
    draw.text(
        (CARD_PADDING, y),
        f"{bank_label}: {phone}",
        fill=ACCENT_COLOR,
        font=font_label,
    )
    y += 20 + 20

    if participants:
        # Разделитель
        draw.line(
            [(CARD_PADDING, y), (CARD_WIDTH - CARD_PADDING, y)],
            fill=DIVIDER_COLOR,
            width=1,
        )
        y += 1 + 16

        settled_count = sum(1 for p in participants if p.is_settled)
        header = f"Должны ({len(participants) - settled_count}/{len(participants)}):"
        draw.text(
            (CARD_PADDING, y),
            header,
            fill=TEXT_SECONDARY,
            font=font_label,
        )
        y += 20 + 8

        for p in participants:
            if p.is_settled:
                line = f"✓  {p.name} — отдал"
                color = PAID_COLOR
            else:
                line = f"○  {p.name} — {_format_amount(p.amount)}"
                color = TEXT_PRIMARY
            draw.text(
                (CARD_PADDING + 8, y),
                line,
                fill=color,
                font=font_participant,
            )
            y += 28

        y += 16
    else:
        # Подсказка — нет участников
        draw.line(
            [(CARD_PADDING, y), (CARD_WIDTH - CARD_PADDING, y)],
            fill=DIVIDER_COLOR,
            width=1,
        )
        y += 1 + 16

        hint1 = "Нажмите «Я должен»,"
        hint2 = "чтобы разделить счёт"
        bbox1 = draw.textbbox((0, 0), hint1, font=font_hint)
        bbox2 = draw.textbbox((0, 0), hint2, font=font_hint)
        draw.text(
            ((CARD_WIDTH - (bbox1[2] - bbox1[0])) / 2, y),
            hint1,
            fill=TEXT_SECONDARY,
            font=font_hint,
        )
        y += 20 + 4
        draw.text(
            ((CARD_WIDTH - (bbox2[2] - bbox2[0])) / 2, y),
            hint2,
            fill=TEXT_SECONDARY,
            font=font_hint,
        )
        y += 20 + 16

    # Футер
    draw.line(
        [(CARD_PADDING, y), (CARD_WIDTH - CARD_PADDING, y)],
        fill=DIVIDER_COLOR,
        width=1,
    )
    y += 1 + 12

    footer = f"{creator_name} • SplitPay"
    bbox = draw.textbbox((0, 0), footer, font=font_footer)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, y),
        footer,
        fill=TEXT_SECONDARY,
        font=font_footer,
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
