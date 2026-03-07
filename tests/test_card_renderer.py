from io import BytesIO

from PIL import Image

from bot.services.card_renderer import render_card


def test_render_card_returns_bytes():
    result = render_card(
        amount=50000,
        description="за ужин",
        creator_username="alice",
        sbp_url="https://qr.nspk.ru/pay?test=1",
        participants=[],
    )
    assert isinstance(result, BytesIO)


def test_render_card_is_valid_image():
    result = render_card(
        amount=50000,
        description="за ужин",
        creator_username="alice",
        sbp_url="https://qr.nspk.ru/pay?test=1",
        participants=[],
    )
    img = Image.open(result)
    assert img.size[0] > 0
    assert img.size[1] > 0


def test_render_card_with_participants():
    result = render_card(
        amount=50000,
        description="за ужин",
        creator_username="alice",
        sbp_url="https://qr.nspk.ru/pay?test=1",
        participants=["bob", "charlie"],
    )
    img = Image.open(result)
    assert img.size[0] > 0
