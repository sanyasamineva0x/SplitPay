"""Генерация GIF-демо для README.

Запуск: python scripts/generate_demo.py
Результат: assets/demo.gif

Показывает 3 кадра:
1. Inline-запрос: @SplitPayBot 3000 за ужин
2. Карточка расхода (без участников)
3. Карточка с участниками (после join)

Стиль: тёмная тема, светло-голубой акцент.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
FONT_PATH = ROOT / "assets" / "fonts" / "Inter-Bold.ttf"
OUTPUT = ROOT / "assets" / "demo.gif"

WIDTH, HEIGHT = 480, 320
BG = (22, 22, 30)
HEADER_BG = (30, 32, 42)
CHAT_BG = (38, 40, 52)
CARD_BG = (42, 44, 58)
ACCENT = (135, 200, 255)  # Светло-голубой
GREEN = (100, 210, 150)
TEXT = (245, 245, 250)
TEXT_DIM = (140, 145, 165)
TEXT_HINT = (100, 105, 125)
BTN_BG = (55, 58, 75)
BTN_BORDER = (75, 78, 95)


def _font(size: int) -> ImageFont.FreeTypeFont:
    return ImageFont.truetype(str(FONT_PATH), size)


def _draw_header(draw: ImageDraw.Draw) -> None:
    """Шапка чата."""
    draw.rectangle((0, 0, WIDTH, 40), fill=HEADER_BG)
    font = _font(14)
    draw.text((20, 12), "Групповой чат", fill=TEXT, font=font)
    # Тонкая линия-разделитель
    draw.line((0, 40, WIDTH, 40), fill=(50, 52, 65), width=1)


def _draw_step_indicator(draw: ImageDraw.Draw, step: int, total: int) -> None:
    """Индикатор шага внизу."""
    font = _font(12)
    label = f"Шаг {step}/{total}"
    draw.text((WIDTH - 80, HEIGHT - 20), label, fill=TEXT_HINT, font=font)
    # Точки
    dot_y = HEIGHT - 16
    for i in range(total):
        x = 20 + i * 16
        color = ACCENT if i < step else (60, 62, 75)
        draw.ellipse((x, dot_y, x + 8, dot_y + 8), fill=color)


def _draw_buttons(draw: ImageDraw.Draw, card_x: int, card_w: int, btn_y: int) -> None:
    """Кнопки «Я должен» и «Я отдал»."""
    font_label = _font(12)
    btn_w = (card_w - 8) // 2

    draw.rounded_rectangle(
        (card_x, btn_y, card_x + btn_w, btn_y + 32),
        radius=8,
        fill=BTN_BG,
        outline=BTN_BORDER,
        width=1,
    )
    draw.text((card_x + 16, btn_y + 8), "Я должен 💰", fill=ACCENT, font=font_label)

    draw.rounded_rectangle(
        (card_x + btn_w + 8, btn_y, card_x + card_w, btn_y + 32),
        radius=8,
        fill=BTN_BG,
        outline=BTN_BORDER,
        width=1,
    )
    draw.text((card_x + btn_w + 24, btn_y + 8), "Я отдал ✓", fill=TEXT, font=font_label)


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
        outline=BTN_BORDER,
        width=1,
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
        radius=10,
        fill=CARD_BG,
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
        fill=TEXT_HINT,
        font=_font(11),
    )

    _draw_step_indicator(draw, 1, 3)
    return img


def frame_2_card_empty() -> Image.Image:
    """Кадр 2: карточка без участников."""
    img = Image.new("RGB", (WIDTH, HEIGHT), BG)
    draw = ImageDraw.Draw(img)
    _draw_header(draw)

    card_x, card_y = 40, 60
    card_w, card_h = WIDTH - 80, 200
    draw.rounded_rectangle(
        (card_x, card_y, card_x + card_w, card_y + card_h),
        radius=16,
        fill=CARD_BG,
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
        fill=ACCENT,
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
        fill=TEXT_HINT,
        font=font_label,
    )
    draw.text(
        (card_x + 24, card_y + 162),
        "чтобы разделить счёт",
        fill=TEXT_HINT,
        font=font_label,
    )

    _draw_buttons(draw, card_x, card_w, card_y + card_h + 8)
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
        radius=16,
        fill=CARD_BG,
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
        fill=ACCENT,
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

    _draw_buttons(draw, card_x, card_w, card_y + card_h + 8)
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
