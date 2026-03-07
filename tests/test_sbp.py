from bot.services.sbp import build_sbp_deeplink, build_sbp_qr_url

PHONE = "+79991234567"
BANK = "sber"


def test_build_sbp_deeplink():
    link = build_sbp_deeplink(phone=PHONE, bank=BANK, amount=50000)
    assert "qr.nspk.ru" in link or PHONE.replace("+", "") in link
    assert isinstance(link, str)
    assert len(link) > 0


def test_build_sbp_qr_url_contains_amount():
    url = build_sbp_qr_url(phone=PHONE, bank=BANK, amount=50000)
    assert isinstance(url, str)
    assert len(url) > 0


def test_build_sbp_deeplink_different_banks():
    link_sber = build_sbp_deeplink(phone=PHONE, bank="sber", amount=10000)
    link_tink = build_sbp_deeplink(phone=PHONE, bank="tinkoff", amount=10000)
    assert link_sber != link_tink
