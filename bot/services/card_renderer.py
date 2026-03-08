from __future__ import annotations

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
DIVIDER_COLOR = "#e5e7eb"


def _format_amount(kopecks: int) -> str:
    """Форматирование суммы в копейках → строка в рублях."""
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


def render_placeholder() -> BytesIO:
    """Генерация placeholder-карточки для inline результата."""
    height = 300
    img = Image.new("RGBA", (CARD_WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_brand = _load_font(36)
    font_sub = _load_font(18)

    # Бренд
    text = "SplitPay"
    bbox = draw.textbbox((0, 0), text, font=font_brand)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, 100),
        text,
        fill=ACCENT_COLOR,
        font=font_brand,
    )

    # Подпись
    sub = "Генерация карточки..."
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, 155),
        sub,
        fill=TEXT_SECONDARY,
        font=font_sub,
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
