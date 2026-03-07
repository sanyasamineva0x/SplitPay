from __future__ import annotations

from io import BytesIO
from pathlib import Path

import qrcode
from PIL import Image, ImageDraw, ImageFont

ASSETS_DIR = Path(__file__).parent.parent.parent / "assets"
FONT_PATH = ASSETS_DIR / "fonts" / "Inter-Bold.ttf"

CARD_WIDTH = 600
CARD_HEIGHT = 400
BG_COLOR = "#1a1a2e"
ACCENT_COLOR = "#e94560"
TEXT_COLOR = "#ffffff"
PAID_COLOR = "#4ecca3"
QR_SIZE = 140


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
    qr = qrcode.QRCode(version=1, box_size=4, border=2)
    qr.add_data(data)
    qr.make(fit=True)
    return qr.make_image(fill_color="#ffffff", back_color=BG_COLOR).convert("RGBA")


def render_card(
    amount: int,
    description: str,
    creator_username: str | None,
    sbp_url: str,
    participants: list[str],
) -> BytesIO:
    """Генерация карточки оплаты в формате PNG."""
    img = Image.new("RGBA", (CARD_WIDTH, CARD_HEIGHT), BG_COLOR)
    draw = ImageDraw.Draw(img)

    font_big = _load_font(48)
    font_mid = _load_font(20)
    font_small = _load_font(16)

    # Сумма
    amount_text = _format_amount(amount)
    bbox = draw.textbbox((0, 0), amount_text, font=font_big)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, 30),
        amount_text,
        fill=TEXT_COLOR,
        font=font_big,
    )

    # Описание
    bbox = draw.textbbox((0, 0), description, font=font_mid)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, 90),
        description,
        fill="#aaaaaa",
        font=font_mid,
    )

    # QR-код
    qr_img = _generate_qr(sbp_url)
    qr_img = qr_img.resize((QR_SIZE, QR_SIZE))
    qr_x = (CARD_WIDTH - QR_SIZE) // 2
    qr_y = 130
    img.paste(qr_img, (qr_x, qr_y))

    # Участники
    if participants:
        y = qr_y + QR_SIZE + 15
        parts_text = "  ".join(f"✓ @{p}" for p in participants)
        bbox = draw.textbbox((0, 0), parts_text, font=font_small)
        text_w = bbox[2] - bbox[0]
        draw.text(
            ((CARD_WIDTH - text_w) / 2, y),
            parts_text,
            fill=PAID_COLOR,
            font=font_small,
        )

    # Футер
    footer = f"@{creator_username} • TGpay" if creator_username else "TGpay"
    bbox = draw.textbbox((0, 0), footer, font=font_small)
    text_w = bbox[2] - bbox[0]
    draw.text(
        ((CARD_WIDTH - text_w) / 2, CARD_HEIGHT - 35),
        footer,
        fill="#666666",
        font=font_small,
    )

    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
