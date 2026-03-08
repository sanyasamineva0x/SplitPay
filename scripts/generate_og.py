"""Генерация OG-картинки для GitHub social preview.

Запуск: python scripts/generate_og.py
Результат: assets/og-preview.png (1280x640)

Стиль: тёмная карточка на тёмном фоне, светло-голубой акцент.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "Inter-Bold.ttf"
OUTPUT = ROOT / "assets" / "og-preview.png"

WIDTH, HEIGHT = 1280, 640

# Цвета
BG_OUTER = (22, 22, 30)
BG_CARD = (42, 44, 58)
ACCENT = (135, 200, 255)  # Светло-голубой
TEXT_WHITE = (245, 245, 250)
TEXT_GRAY = (160, 165, 185)
TEXT_DIM = (110, 115, 135)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _draw_glow(draw: ImageDraw.Draw, cx: int, cy: int, radius: int) -> None:
    """Мягкое свечение — несколько полупрозрачных кругов."""
    for i in range(6):
        r = radius - i * (radius // 6)
        alpha = 8 + i * 3
        color = (ACCENT[0], ACCENT[1], ACCENT[2])
        # Имитация свечения через круги с убывающей яркостью
        glow_color = (
            BG_OUTER[0] + (color[0] - BG_OUTER[0]) * alpha // 255,
            BG_OUTER[1] + (color[1] - BG_OUTER[1]) * alpha // 255,
            BG_OUTER[2] + (color[2] - BG_OUTER[2]) * alpha // 255,
        )
        draw.ellipse(
            (cx - r, cy - r, cx + r, cy + r),
            fill=glow_color,
        )


def generate() -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_OUTER)
    draw = ImageDraw.Draw(img)

    # Фоновое свечение (вверху справа)
    _draw_glow(draw, WIDTH - 200, 120, 300)

    # Карточка
    card_margin = 60
    card_top = 50
    card_bottom = HEIGHT - 50
    draw.rounded_rectangle(
        (card_margin, card_top, WIDTH - card_margin, card_bottom),
        radius=28,
        fill=BG_CARD,
    )

    font_title = _load_font(80)
    font_sub = _load_font(26)
    font_example = _load_font(22)
    font_stack = _load_font(18)

    # Контент внутри карточки
    content_x = card_margin + 70
    content_y = card_top + 60

    # Заголовок — жирный, светло-голубой
    draw.text(
        (content_x, content_y),
        "SplitPay",
        fill=ACCENT,
        font=font_title,
    )

    # Подзаголовок — белый
    draw.text(
        (content_x, content_y + 100),
        "Inline Telegram-бот",
        fill=TEXT_WHITE,
        font=font_sub,
    )
    draw.text(
        (content_x, content_y + 140),
        "для разделения расходов между друзьями",
        fill=TEXT_GRAY,
        font=font_sub,
    )

    # Пример — в «пилюле»
    example = "@SplitPayBot 3000 за ужин"
    bbox = draw.textbbox((0, 0), example, font=font_example)
    ew = bbox[2] - bbox[0]
    eh = bbox[3] - bbox[1]

    pill_x = content_x
    pill_y = content_y + 230
    pad_x, pad_y = 24, 14
    draw.rounded_rectangle(
        (pill_x, pill_y, pill_x + ew + pad_x * 2, pill_y + eh + pad_y * 2),
        radius=22,
        fill=(55, 58, 75),
        outline=(80, 85, 110),
        width=1,
    )
    draw.text(
        (pill_x + pad_x, pill_y + pad_y),
        example,
        fill=ACCENT,
        font=font_example,
    )

    # Стек — внизу карточки
    stack = "Python · aiogram 3 · SQLAlchemy · Pillow"
    draw.text(
        (content_x, card_bottom - 70),
        stack,
        fill=TEXT_DIM,
        font=font_stack,
    )

    # Декоративный кружок справа (имитация 3D-элемента)
    circle_cx = WIDTH - card_margin - 220
    circle_cy = HEIGHT // 2
    circle_r = 100

    # Градиент-кружок (несколько слоёв)
    for i in range(circle_r, 0, -1):
        t = i / circle_r
        color = (
            int(ACCENT[0] * 0.3 + BG_CARD[0] * 0.7 * t + ACCENT[0] * (1 - t) * 0.5),
            int(ACCENT[1] * 0.3 + BG_CARD[1] * 0.7 * t + ACCENT[1] * (1 - t) * 0.5),
            int(ACCENT[2] * 0.3 + BG_CARD[2] * 0.7 * t + ACCENT[2] * (1 - t) * 0.5),
        )
        draw.ellipse(
            (circle_cx - i, circle_cy - i, circle_cx + i, circle_cy + i),
            fill=color,
        )

    # Символ внутри кружка
    draw.text(
        (circle_cx - 28, circle_cy - 26),
        "₽",
        fill=TEXT_WHITE,
        font=_load_font(56),
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(OUTPUT))
    print(f"Сохранено: {OUTPUT} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    generate()
