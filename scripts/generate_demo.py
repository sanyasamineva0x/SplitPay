"""Генерация GIF-демо для README.

Запуск: python scripts/generate_demo.py
Результат: assets/demo.gif

Показывает 3 кадра:
1. Inline-запрос: @SplitPayBot 3000 за ужин
2. Карточка расхода (без участников)
3. Карточка с участниками (после join)
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "Inter-Bold.ttf"
OUTPUT = ROOT / "assets" / "demo.gif"

WIDTH, HEIGHT = 480, 320
BG = (30, 30, 40)
CHAT_BG = (45, 45, 55)
BUBBLE_BG = (55, 55, 70)
ACCENT = (99, 102, 241)
GREEN = (72, 187, 120)
TEXT = (255, 255, 255)
TEXT_DIM = (160, 160, 180)
BTN_BG = (70, 70, 90)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _draw_header(draw: ImageDraw.Draw) -> None:
    """Шапка чата."""
    draw.rectangle((0, 0, WIDTH, 40), fill=(35, 35, 50))
    font = _font(14)
    draw.text((20, 12), "Групповой чат", fill=TEXT, font=font)


def _draw_step_indicator(draw: ImageDraw.Draw, step: int, total: int) -> None:
    """Индикатор шага внизу."""
    font = _font(12)
    label = f"Шаг {step}/{total}"
    draw.text((WIDTH - 80, HEIGHT - 20), label, fill=TEXT_DIM, font=font)
    # Точки
    dot_y = HEIGHT - 16
    for i in range(total):
        x = 20 + i * 16
        color = ACCENT if i < step else (80, 80, 100)
        draw.ellipse((x, dot_y, x + 8, dot_y + 8), fill=color)


def frame_1_inline_query() -> Image.Image:
    """Кадр 1: набор inline-запроса."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_header(draw)

    font_msg = _font(14)
    font_input = _font(16)

    # Поле ввода
    input_y = HEIGHT - 60
    draw.rounded_rectangle(
        (15, input_y, WIDTH - 15, input_y + 36),
        radius=18,
        fill=CHAT_BG,
    )

    # Текст в поле ввода
    draw.text(
        (28, input_y + 8),
        "@SplitPayBot 3000 за ужин",
        fill=ACCENT,
        font=font_input,
    )

    # Подсказка — результат inline
    result_y = input_y - 56
    draw.rounded_rectangle(
        (15, result_y, WIDTH - 15, result_y + 44),
        radius=8,
        fill=BUBBLE_BG,
    )
    draw.text(
        (28, result_y + 6),
        "3 000 ₽ — за ужин",
        fill=TEXT,
        font=font_msg,
    )
    draw.text(
        (28, result_y + 24),
        "Нажмите, чтобы отправить в чат",
        fill=TEXT_DIM,
        font=_font(11),
    )

    _draw_step_indicator(draw, 1, 3)
    return img


def frame_2_card_empty() -> Image.Image:
    """Кадр 2: карточка без участников."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_header(draw)

    # Карточка
    card_x, card_y = 40, 60
    card_w, card_h = WIDTH - 80, 200
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w, card_y + card_h),
        radius=12,
        fill=BUBBLE_BG,
    )

    font_amount = _font(32)
    font_desc = _font(14)
    font_label = _font(12)

    # Сумма
    draw.text((card_x + 24, card_y + 16), "3 000 ₽", fill=TEXT, font=font_amount)
    draw.text((card_x + 24, card_y + 56), "за ужин", fill=TEXT_DIM, font=font_desc)

    # Реквизиты
    draw.text(
        (card_x + 24, card_y + 90),
        "Заплатил: @petya",
        fill=TEXT_DIM,
        font=font_label,
    )
    draw.text(
        (card_x + 24, card_y + 110),
        "Сбер: +7 999 123 45 67",
        fill=TEXT_DIM,
        font=font_label,
    )

    # Подсказка
    draw.text(
        (card_x + 24, card_y + 145),
        "Нажмите «Я должен»,",
        fill=(120, 120, 150),
        font=font_label,
    )
    draw.text(
        (card_x + 24, card_y + 162),
        "чтобы разделить счёт",
        fill=(120, 120, 150),
        font=font_label,
    )

    # Кнопки
    btn_y = card_y + card_h + 8
    btn_w = (card_w - 8) // 2
    draw.rounded_rectangle(
        (card_x, btn_y, card_x + btn_w, btn_y + 32),
        radius=6,
        fill=BTN_BG,
    )
    draw.text((card_x + 16, btn_y + 8), "Я должен 💰", fill=TEXT, font=font_label)

    draw.rounded_rectangle(
        (card_x + btn_w + 8, btn_y, card_x + card_w, btn_y + 32),
        radius=6,
        fill=BTN_BG,
    )
    draw.text((card_x + btn_w + 24, btn_y + 8), "Я отдал ✓", fill=TEXT, font=font_label)

    _draw_step_indicator(draw, 2, 3)
    return img


def frame_3_card_with_participants() -> Image.Image:
    """Кадр 3: карточка с участниками."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_header(draw)

    card_x, card_y = 40, 60
    card_w, card_h = WIDTH - 80, 200
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w, card_y + card_h),
        radius=12,
        fill=BUBBLE_BG,
    )

    font_amount = _font(32)
    font_desc = _font(14)
    font_label = _font(12)

    # Сумма
    draw.text((card_x + 24, card_y + 16), "3 000 ₽", fill=TEXT, font=font_amount)
    draw.text((card_x + 24, card_y + 56), "за ужин", fill=TEXT_DIM, font=font_desc)

    # Реквизиты
    draw.text(
        (card_x + 24, card_y + 90),
        "Заплатил: @petya",
        fill=TEXT_DIM,
        font=font_label,
    )

    # Участники
    participants = [
        ("○ @vasya — 1 000 ₽", TEXT_DIM),
        ("✓ @masha — 1 000 ₽", GREEN),
        ("○ @kolya — 1 000 ₽", TEXT_DIM),
    ]
    for i, (line, color) in enumerate(participants):
        draw.text(
            (card_x + 24, card_y + 120 + i * 20),
            line,
            fill=color,
            font=font_label,
        )

    # Кнопки
    btn_y = card_y + card_h + 8
    btn_w = (card_w - 8) // 2
    draw.rounded_rectangle(
        (card_x, btn_y, card_x + btn_w, btn_y + 32),
        radius=6,
        fill=BTN_BG,
    )
    draw.text((card_x + 16, btn_y + 8), "Я должен 💰", fill=TEXT, font=font_label)

    draw.rounded_rectangle(
        (card_x + btn_w + 8, btn_y, card_x + card_w, btn_y + 32),
        radius=6,
        fill=BTN_BG,
    )
    draw.text((card_x + btn_w + 24, btn_y + 8), "Я отдал ✓", fill=TEXT, font=font_label)

    _draw_step_indicator(draw, 3, 3)
    return img


def main() -> None:
    frames = [
        frame_1_inline_query(),
        frame_2_card_empty(),
        frame_3_card_with_participants(),
    ]

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    frames[0].save(
        str(OUTPUT),
        save_all=True,
        append_images=frames[1:],
        duration=2500,
        loop=0,
    )
    print(f"Сохранено: {OUTPUT}")


if __name__ == "__main__":
    main()
