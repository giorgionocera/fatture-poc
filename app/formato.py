"""Formati italiani per importi, numeri, date e nomi."""
import re

MESI = ["", "gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre",
        "ottobre", "novembre", "dicembre"]


def numero(x: float, decimali: int = 2) -> str:
    testo = f"{x:,.{decimali}f}"
    return testo.replace(",", "§").replace(".", ",").replace("§", ".")


def euro(x: float) -> str:
    return numero(x, 2) + " €"


def prezzo(x: float) -> str:
    """Due decimali, tre se servono (0,212 € al kWh)."""
    return numero(x, 2 if abs(round(x, 2) - x) < 1e-9 else 3) + " €"


def percento(x: float) -> str:
    return numero(x, 1) + "%"


def intero(x: float) -> str:
    return numero(x, 0)


def data(iso: str) -> str:
    a, m, g = iso.split("-")
    return f"{g}/{m}/{a}"


def mese(iso: str) -> str:
    """'2026-07' -> 'luglio 2026'."""
    a, m = iso.split("-")[:2]
    return f"{MESI[int(m)]} {a}"


def nome_breve(fornitore: str) -> str:
    return re.sub(r"\s+(S\.r\.l\.|S\.p\.A\.|S\.n\.c\.|S\.a\.s\.|Soc\. Coop\.)$", "", fornitore or "")


def del_giorno(iso: str) -> str:
    """'dell'11/11/2025', 'del 03/06/2026'."""
    return ("dell'" if int(iso[8:10]) in (1, 8, 11) else "del ") + data(iso)


def il_giorno(iso: str) -> str:
    return ("l'" if int(iso[8:10]) in (1, 8, 11) else "il ") + data(iso)
