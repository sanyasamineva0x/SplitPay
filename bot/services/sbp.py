from urllib.parse import urlencode

BANK_IDS: dict[str, str] = {
    "sber": "100000000111",
    "tinkoff": "100000000004",
    "alfa": "100000000008",
    "vtb": "100000000005",
    "raiffeisen": "100000000007",
}


def _phone_to_sbp(phone: str) -> str:
    return phone.replace("+", "").replace("-", "").replace(" ", "")


def build_sbp_deeplink(phone: str, bank: str, amount: int) -> str:
    """СБП deeplink для открытия приложения банка.
    amount в копейках.
    """
    phone_clean = _phone_to_sbp(phone)
    params = {
        "type": "02",
        "bank": BANK_IDS.get(bank, "100000000111"),
        "sum": str(amount),
        "cur": "RUB",
        "crc": "0000",
        "st": phone_clean,
    }
    return f"https://qr.nspk.ru/pay?{urlencode(params)}"


def build_sbp_qr_url(phone: str, bank: str, amount: int) -> str:
    """URL для генерации QR-кода (тот же deeplink)."""
    return build_sbp_deeplink(phone=phone, bank=bank, amount=amount)
