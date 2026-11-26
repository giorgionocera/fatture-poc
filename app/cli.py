"""Riga di comando: batteria delle domande di prova, domanda singola, verifica del caricamento.

  python -m app.cli verifica            numeri del caricamento e delle quattro regole
  python -m app.cli domanda "..."       una domanda, con cifre, interrogazioni e fatture
  python -m app.cli prova [numeri...]   le 25 domande di prova, con resoconto in lavoro/resoconto_prova.md
  python -m app.cli riformulazioni      le 25 domande chieste in altri due modi (prove/riformulazioni.json)
  python -m app.cli fuori               dieci domande su cose che nelle fatture non ci sono (prove/fuori_dai_dati.json)
"""
import asyncio
import json
import re
import sys
import time
from datetime import datetime

from . import caricamento, cifre
from .agente import Agente, per_la_storia
from .config import LAVORO, RADICE, carica_config, file_fornitori
from .modello import Modello
from .registro import Registro
from .strumenti import Dati

FATTURE = RADICE / "contesto" / "dati" / "fatture"
DOMANDE = RADICE / "contesto" / "dati" / "domande_di_prova.json"
FILE_DB = LAVORO / "prova.db"
RESOCONTO = LAVORO / "resoconto_prova.md"
IN_LETTERE = {"un": 1, "uno": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6, "sette": 7,
              "otto": 8, "nove": 9, "dieci": 10, "undici": 11, "dodici": 12, "sedici": 16, "venti": 20}


def prepara() -> tuple[dict, Agente]:
    cfg = carica_config()
    numeri = caricamento.carica(FATTURE, file_fornitori(cfg), FILE_DB)
    m = cfg["modello"]
    dati = Dati(FILE_DB, m.get("righe_massime", 200), m.get("secondi_interrogazione", 5))
    return numeri, Agente(cfg, Modello(cfg), dati, Registro(LAVORO / "registro_prova.jsonl"))


def cifre_presenti(testo: str, attese: list[float]) -> list[float]:
    """Le cifre attese che mancano nel testo della risposta."""
    letture = [l for n in cifre.numeri_del_testo(testo) for l in n["letture"]]
    letture += [(float(v), 0) for parola, v in IN_LETTERE.items() if re.search(rf"(?i)\b{parola}\b", testo)]
    mancanti = []
    for attesa in attese:
        decimali = len(str(attesa).split(".")[1]) if "." in str(attesa) and not float(attesa).is_integer() else 0
        # vale anche la stessa cifra scritta con più decimali: 52,43% per 52,4%
        if not any(abs(abs(attesa) - n) <= 0.5 * 10 ** -d + 1e-9 or abs(round(n, decimali) - abs(attesa)) <= 1e-9 for n, d in letture):
            mancanti.append(attesa)
    return mancanti


def giudica(domanda: dict, scheda: dict) -> tuple[str, str]:
    if scheda["esito"] == "errore":
        return "errore", scheda.get("dettaglio", "")
    if scheda["esito"] == "limite":
        return "senza risposta", "l'agente si è fermato senza una risposta"
    if scheda["esito"] == "solo_dati":
        return "solo dati", "il controllo delle cifre ha fermato la frase: mostrata solo la tabella"
    attese = domanda["cifre_attese"]
    if not attese:
        ha_importi = re.search(r"\d[\d.]*,\d{2}\s?€|€\s?\d", scheda["testo"])
        lo_dice = re.search(r"(?i)\bnon (c'è|ci sono|lo so|so|posso|risult|compa|conosco|ho |sono |è possibile|si può|si possono|si ricava|si vede|dicono|riport)|solo (le fatture|gli acquisti)", scheda["testo"])
        if not lo_dice:
            return "sbagliata", "non dice chiaramente che il dato non c'è"
        return "giusta", ("dice che non c'è, ma aggiunge un importo non richiesto" if ha_importi else "")
    mancanti = cifre_presenti(scheda["testo"], attese)
    if not mancanti:
        return "giusta", ""
    if len(mancanti) < len(attese):
        return "incompleta", "mancano: " + ", ".join(str(m) for m in mancanti)
    return "sbagliata", "mancano: " + ", ".join(str(m) for m in mancanti)


async def prova(quali: list[int], file_domande=None, nome="prova", con_storia=True):
    numeri, agente = prepara()
    resoconto = LAVORO / f"resoconto_{nome}.md"
    domande = json.loads((RADICE / file_domande if file_domande else DOMANDE).read_text(encoding="utf-8"))
    if quali:
        domande = [d for d in domande if d["numero"] in quali]
    esiti, schede = [], []
    for d in domande:
        t = time.monotonic()
        storia = per_la_storia(schede, agente.imp.get("domande_ricordate", 4)) if con_storia else []
        scheda = await agente.rispondi(d["domanda"], storia)
        schede.append(scheda)
        giudizio, motivo = giudica(d, scheda)
        esiti.append((d, scheda, giudizio, motivo, time.monotonic() - t))
        print(f"{d['numero']:>3} {giudizio:<15} {esiti[-1][4]:5.1f}s  {d['domanda']}\n   → {scheda['testo']}" + (f"\n   ! {motivo}" if motivo else ""), flush=True)

    giuste = sum(1 for e in esiti if e[2] == "giusta")
    sbagliate = [e for e in esiti if e[2] in ("sbagliata", "incompleta")]
    righe = [f"# Resoconto della prova – {datetime.now():%d/%m/%Y %H:%M}", "",
             f"Modello: `{agente.modello.nome}` · fatture caricate: {numeri['file']}", "",
             f"**{giuste} su {len(esiti)} giuste al primo tentativo.** "
             f"Tempo medio {sum(e[4] for e in esiti) / max(1, len(esiti)):.1f} s, massimo {max(e[4] for e in esiti):.1f} s.", "",
             "Una risposta è *giusta* se contiene tutte le cifre attese; *incompleta* se ne manca qualcuna; "
             "*solo dati* se il controllo delle cifre ha fermato la frase (nessuna cifra sbagliata è andata a schermo).", "",
             "| # | Domanda | Esito | Secondi | Passi |", "| --- | --- | --- | --- | --- |"]
    for d, s, g, motivo, sec in esiti:
        righe.append(f"| {d['numero']} | {d['domanda']} | {g} | {sec:.1f} | {len(s['interrogazioni'])} |")
    if sbagliate:
        righe += ["", "## Da guardare", ""]
        righe += [f"- **{d['numero']}. {d['domanda']}** – {g}: {motivo}. Atteso: {d['cifre_attese']} {d['nota']}" for d, s, g, motivo, _ in sbagliate]
    righe += ["", "## Risposte", ""]
    for d, s, g, motivo, sec in esiti:
        righe += [f"### {d['numero']}. {d['domanda']}", "", f"{g} · {sec:.1f} s" + (f" · {motivo}" if motivo else ""), "",
                  f"> {s['testo']}", "", f"Atteso: {d['cifre_attese']} {d['nota']}".rstrip(), ""]
        righe += [f"```sql\n{q}\n```" for q in s["interrogazioni"]] + [""]
    resoconto.write_text("\n".join(righe), encoding="utf-8")
    print(f"\n{giuste} su {len(esiti)} giuste. Resoconto: lavoro/{resoconto.name}")
    return giuste, len(esiti)


async def domanda(testo: str):
    _, agente = prepara()
    scheda = await agente.rispondi(testo, su_passo=lambda t: print("  …", t, flush=True))
    print(json.dumps(scheda, ensure_ascii=False, indent=2))


def verifica():
    numeri, agente = prepara()
    a = agente.analisi()
    print(json.dumps(numeri, ensure_ascii=False, indent=2))
    for v in a["voci_recuperabili"]:
        print(f"  {v['importo']:>9.2f}  {v['titolo']} – {v['dettaglio']}")
    print(f"  {a['recuperabile_totale']:>9.2f}  TOTALE RECUPERABILE")


if __name__ == "__main__":
    comando = sys.argv[1] if len(sys.argv) > 1 else ""
    if comando == "prova":
        asyncio.run(prova([int(x) for x in sys.argv[2:]]))
    elif comando == "riformulazioni":   # ogni domanda è indipendente: nessuna memoria delle precedenti
        asyncio.run(prova([], "prove/riformulazioni.json", "riformulazioni", con_storia=False))
    elif comando == "fuori":
        asyncio.run(prova([], "prove/fuori_dai_dati.json", "fuori_dai_dati", con_storia=False))
    elif comando == "domanda" and len(sys.argv) > 2:
        asyncio.run(domanda(" ".join(sys.argv[2:])))
    elif comando == "verifica":
        verifica()
    else:
        print(__doc__)
