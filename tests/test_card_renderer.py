from io import BytesIO

from PIL import Image

from bot.services.card_renderer import render_placeholder


def test_render_placeholder_returns_bytes():
    result = render_placeholder()
    assert isinstance(result, BytesIO)


def test_render_placeholder_is_valid_image():
    result = render_placeholder()
    img = Image.open(result)
    assert img.size[0] > 0
    assert img.size[1] > 0
