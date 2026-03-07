from __future__ import annotations

from io import BytesIO
from pathlib import Path

import qrcode
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
DIVIDER_COLOR = "#e5e7eb"
QR_BG = "#f9fafb"

QR_SIZE = 180


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


def _generate_qr(data: str) -> Image.Image:
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="#1a1a1a", back_color=QR_BG).convert("RGBA")


def render_card(
    amount: int,
    description: str,
    creator_username: str | None,
    sbp_url: str,
    participants: list[str],
) -> BytesIO:
    """Генерация карточки оплаты — минималистичный светлый стиль."""
    font_amount = _load_font(52)
    font_desc = _load_font(20)
    font_label = _load_font(15)
    font_participant = _load_font(16)
    font_footer = _load_font(14)

    # Расчёт высоты карточки (динамическая)
    y = CARD_PADDING
    y += 60  # сумма
    y += 10  # отступ
    y += 28  # описание
    y += 20  # отступ до разделителя
    y += 1   # разделитель
    y += 20  # отступ после разделителя
    y += QR_SIZE  # QR-код
    y += 8   # отступ
    y += 20  # подпись "Наведите камеру"
    y += 20  # отступ

    if participants:
        y += 1   # разделитель
        y += 16  # отступ
        y += 20  # заголовок "Оплатили:"
        y += 8   # отступ
        y += len(participants) * 26  # участники
        y += 16  # отступ

    y += 1   # разделитель футера
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
    y += 60

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

    # QR-код по центру на светлом фоне
    y += 20
    qr_img = _generate_qr(sbp_url)
    qr_img = qr_img.resize((QR_SIZE, QR_SIZE))
    qr_x = (CARD_WIDTH - QR_SIZE) // 2
    # Фон под QR
    draw.rounded_rectangle(
        [(qr_x - 10, y - 10), (qr_x + QR_SIZE + 10, y + QR_SIZE + 10)],
        radius=8,
        fill=QR_BG,
    )
    img.paste(qr_img, (qr_x, y))
    y += QR_SIZE

    # Подпись под QR
    y += 8
    label = "Оплатить через СБП →"
    bbox = draw.textbbox((0, 0), label, font=font_label)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, y),
        label,
        fill=ACCENT_COLOR,
        font=font_label,
    )
    y += 20

    # Участники
    y += 20
    if participants:
        draw.line(
            [(CARD_PADDING, y), (CARD_WIDTH - CARD_PADDING, y)],
            fill=DIVIDER_COLOR,
            width=1,
        )
        y += 1 + 16

        header = f"Оплатили ({len(participants)}):"
        draw.text(
            (CARD_PADDING, y),
            header,
            fill=TEXT_SECONDARY,
            font=font_label,
        )
        y += 20 + 8

        for name in participants:
            line = f"✓  @{name}"
            draw.text(
                (CARD_PADDING + 8, y),
                line,
                fill=PAID_COLOR,
                font=font_participant,
            )
            y += 26

        y += 16

    # Футер
    draw.line(
        [(CARD_PADDING, y), (CARD_WIDTH - CARD_PADDING, y)],
        fill=DIVIDER_COLOR,
        width=1,
    )
    y += 1 + 12

    footer = f"@{creator_username} • TGpay" if creator_username else "TGpay"
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


def render_placeholder() -> BytesIO:
    """Генерация placeholder-карточки для inline результата."""
    height = 300
    img = Image.new("RGBA", (CARD_WIDTH, height), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_brand = _load_font(36)
    font_sub = _load_font(18)

    # Бренд
    text = "TGpay"
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
