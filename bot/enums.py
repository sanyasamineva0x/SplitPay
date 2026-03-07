from enum import Enum


class BankName(str, Enum):
    SBER = "sber"
    TINKOFF = "tinkoff"
    ALFA = "alfa"
    VTB = "vtb"
    RAIFFEISEN = "raiffeisen"
