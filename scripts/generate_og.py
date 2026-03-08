"""Генерация OG-картинки для GitHub social preview.

Запуск: python scripts/generate_og.py
Результат: assets/og-preview.png (1280x640)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "Inter-Bold.ttf"
OUTPUT = ROOT / "assets" / "og-preview.png"

WIDTH, HEIGHT = 1280, 640
BG_COLOR = (25, 25, 35)
ACCENT = (99, 102, 241)
TEXT_COLOR = (255, 255, 255)
TEXT_SECONDARY = (180, 180, 200)


def _load_font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def generate() -> None:
    img = Image.new("RGB", (WIDTH, HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_title = _load_font(72)
    font_sub = _load_font(28)
    font_example = _load_font(22)

    # Заголовок
    title = "SplitPay"
    bbox = draw.textbbox((0, 0), title, font=font_title)
    tw = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - tw) // 2, 160),
        title,
        fill=ACCENT,
        font=font_title,
    )

    # Подзаголовок
    sub = "Inline Telegram-бот для разделения расходов"
    bbox = draw.textbbox((0, 0), sub, font=font_sub)
    sw = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - sw) // 2, 260),
        sub,
        fill=TEXT_COLOR,
        font=font_sub,
    )

    # Пример использования
    example = "@SplitPayBot 3000 за ужин"
    bbox = draw.textbbox((0, 0), example, font=font_example)
    ew = bbox[2] - bbox[0]
    eh = bbox[3] - bbox[1]

    # Фон для примера
    pad_x, pad_y = 24, 12
    ex = (WIDTH - ew) // 2
    ey = 360
    draw.rounded_rectangle(
        (ex - pad_x, ey - pad_y, ex + ew + pad_x, ey + eh + pad_y),
        radius=8,
        fill=(45, 45, 60),
    )
    draw.text((ex, ey), example, fill=TEXT_SECONDARY, font=font_example)

    # Стек
    stack = "Python · aiogram 3 · SQLAlchemy · Pillow"
    bbox = draw.textbbox((0, 0), stack, font=font_example)
    stw = bbox[2] - bbox[0]
    draw.text(
        ((WIDTH - stw) // 2, 480),
        stack,
        fill=(120, 120, 140),
        font=font_example,
    )

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    img.save(str(OUTPUT))
    print(f"Сохранено: {OUTPUT} ({WIDTH}x{HEIGHT})")


if __name__ == "__main__":
    generate()
