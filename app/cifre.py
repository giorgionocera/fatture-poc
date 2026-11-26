"""Controllo delle cifre: ogni numero scritto dal modello deve comparire nei risultati degli strumenti.

Una cifra del testo è buona se, a meno di arrotondamento e formato, coincide con:
 - un valore dei risultati degli strumenti di quella domanda (anche dentro un testo, come "conf. 100 pz");
 - il numero di righe di un risultato ("sei fornitori" scritto "6 fornitori");
 - un numero scritto nella domanda o nelle interrogazioni (le costanti che il modello ha messo nel filtro).
I numeri scritti in lettere non vengono controllati.
"""
import re

_NUMERO_TESTO = re.compile(r"(?<![\w])(\d{1,3}(?:\.\d{3})+(?:,\d+)?|\d+(?:[.,]\d+)?)")
_NUMERO_GREZZO = re.compile(r"\d+(?:[.,]\d+)?")


def _letture(grezzo: str) -> list[tuple[float, int]]:
    """Le letture possibili di un numero scritto: (valore, decimali). '1.008' può essere 1008 o 1,008."""
    letture = []
    if "," in grezzo:
        intero, dec = grezzo.split(",")
        letture.append((float(intero.replace(".", "") + "." + dec), len(dec)))
    elif "." in grezzo:
        if re.fullmatch(r"\d{1,3}(\.\d{3})+", grezzo) and not grezzo.startswith("0."):
            letture.append((float(grezzo.replace(".", "")), 0))
        intero, dec = grezzo.rsplit(".", 1)
        if "." not in intero:
            letture.append((float(grezzo), len(dec)))
    else:
        letture.append((float(grezzo), 0))
    return letture


def numeri_del_testo(testo: str) -> list[dict]:
    trovati = []
    for m in _NUMERO_TESTO.finditer(testo or ""):
        seguito = testo[m.end():m.end() + 2].lstrip()
        trovati.append({"grezzo": m.group(1), "letture": _letture(m.group(1)), "percento": seguito.startswith("%")})
    return trovati


def valori_ammessi(risultati: list, testi: list[str] = ()) -> list[float]:
    """Tutti i numeri che compaiono nei risultati (anche dentro i testi) e nei testi indicati."""
    valori: list[float] = []

    def dal_testo(s: str):
        for g in _NUMERO_GREZZO.findall(s):
            valori.append(float(g.replace(",", ".")))
            if "." in g or "," in g:  # "2025.11" o "1,50": anche i pezzi separati
                valori.extend(float(p) for p in re.split(r"[.,]", g) if p)

    def visita(x):
        if isinstance(x, bool) or x is None:
            return
        if isinstance(x, (int, float)):
            valori.append(abs(float(x)))
        elif isinstance(x, str):
            dal_testo(x)
        elif isinstance(x, dict):
            if isinstance(x.get("righe"), list):
                valori.append(float(len(x["righe"])))
            for v in x.values():
                visita(v)
        elif isinstance(x, (list, tuple)):
            valori.append(float(len(x)))
            for v in x:
                visita(v)

    visita(risultati)
    for t in testi:
        dal_testo(t or "")
    return valori


def _torna(lettura: tuple[float, int], percento: bool, valori: list[float]) -> bool:
    n, decimali = lettura
    margine = 0.5 * 10 ** -decimali + 1e-9
    for v in valori:
        if abs(v - n) <= margine or abs(round(v, decimali) - n) <= 1e-9:
            return True
        if percento and abs(v * 100 - n) <= margine:
            return True
    return False


def non_verificate(testo: str, risultati: list, testi_ammessi: list[str] = ()) -> list[str]:
    """Le cifre del testo che non compaiono nei risultati. Lista vuota = la risposta si può mostrare."""
    valori = valori_ammessi(risultati, testi_ammessi)
    sbagliate = []
    for numero in numeri_del_testo(testo):
        if numero["percento"] and numero["grezzo"] == "100":
            continue
        if not any(_torna(l, numero["percento"], valori) for l in numero["letture"]):
            sbagliate.append(numero["grezzo"])
    return sbagliate
