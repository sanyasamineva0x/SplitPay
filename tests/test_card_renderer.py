from io import BytesIO

from PIL import Image

from bot.services.card_renderer import Participant, render_card


def test_render_card_no_participants():
    """Карточка без участников — показывает подсказку."""
    result = render_card(
        amount=300000,
        description="за ужин",
        creator_name="@petya",
        bank_label="Сбер",
        phone="+7 999 123 45 67",
        participants=[],
    )
    assert isinstance(result, BytesIO)
    img = Image.open(result)
    assert img.size[0] == 600
    assert img.size[1] > 200


def test_render_card_with_participants():
    """Карточка с участниками — список должников."""
    result = render_card(
        amount=300000,
        description="за ужин",
        creator_name="@petya",
        bank_label="Сбер",
        phone="+7 999 123 45 67",
        participants=[
            Participant(name="@vasya", amount=100000, is_settled=False),
            Participant(name="@masha", amount=100000, is_settled=True),
        ],
    )
    img = Image.open(result)
    assert img.size[0] == 600
    # С участниками карточка выше
    assert img.size[1] > 300


def test_render_card_with_kopecks():
    """Суммы с копейками отображаются корректно."""
    result = render_card(
        amount=33334,
        description="кофе",
        creator_name="@alice",
        bank_label="Т-Банк",
        phone="+79990001122",
        participants=[
            Participant(name="@bob", amount=33334, is_settled=False),
        ],
    )
    img = Image.open(result)
    assert img.size[0] == 600


def test_render_card_many_participants():
    """Карточка с большим количеством участников."""
    participants = [
        Participant(name=f"@user{i}", amount=10000, is_settled=i % 2 == 0)
        for i in range(8)
    ]
    result = render_card(
        amount=80000,
        description="большая вечеринка",
        creator_name="@host",
        bank_label="Альфа",
        phone="+79998887766",
        participants=participants,
    )
    img = Image.open(result)
    assert img.size[0] == 600
    assert img.size[1] > 400
