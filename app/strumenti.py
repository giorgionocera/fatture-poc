"""I quattro strumenti dell'agente e l'accesso in sola lettura alla base dati."""
import json
import re
import sqlite3
import time
from pathlib import Path

from . import regole

CONVENZIONI = [
    "Leggi sempre dalle viste fatture_valide e righe_valide: escludono i doppioni.",
    "Spesa = imponibile (IVA esclusa). Il totale con IVA è la colonna totale.",
    "Le note di credito (tipo_documento = 'TD04') hanno importi e quantità col segno meno; le fatture sono 'TD01'.",
    "L'articolo è la descrizione della riga. Solo per gli smalti il colore sta nella colonna variante.",
    "Le date sono testo AAAA-MM-GG, i mesi AAAA-MM.",
    "giorni_pagamento = giorni tra la data della fattura e la scadenza (0 = pagamento alla data della fattura).",
    "righe_valide.fattura_id si collega a fatture_valide.id.",
]

COLONNE = {
    "fatture_valide": "id, file, fornitore, partita_iva, comune, provincia, regione, categoria, tipo_documento, numero, "
                      "data, mese, imponibile, iva, totale, scadenza, giorni_pagamento, causale",
    "righe_valide": "id, fattura_id, fornitore, categoria, data, mese, descrizione, articolo, variante, quantita, unita, "
                    "prezzo_unitario, importo, aliquota_iva",
}

STRUMENTI = [
    {"type": "function", "function": {
        "name": "struttura_dati",
        "description": "Tabelle, colonne, convenzioni, elenco di categorie, fornitori e articoli, periodo coperto.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "analisi_iniziale",
        "description": "I risultati delle quattro regole della prima analisi: fatture doppie, aumenti di prezzo, "
                       "stesso articolo a prezzi diversi tra fornitori, canoni pagati dopo la fine di un noleggio.",
        "parameters": {"type": "object", "properties": {}}}},
    {"type": "function", "function": {
        "name": "interroga",
        "description": "Esegue un'interrogazione SQL di sola lettura (SQLite, solo SELECT) sulle fatture. "
                       "Restituisce al massimo 200 righe.",
        "parameters": {"type": "object", "properties": {
            "sql": {"type": "string", "description": "Una sola SELECT sulle viste fatture_valide e righe_valide."},
            "cosa_cerco": {"type": "string", "description": "In parole semplici cosa stai guardando, per esempio 'le fatture della luce'."}},
            "required": ["sql", "cosa_cerco"]}}},
    {"type": "function", "function": {
        "name": "mostra_grafico",
        "description": "Disegna un grafico a schermo. Linea per andamenti nel tempo; barre per confronti tra più di tre voci; "
                       "torta solo per come si divide un totale in parti (valori positivi; oltre cinque parti le altre finiscono in «Altre»).",
        "parameters": {"type": "object", "properties": {
            "tipo": {"type": "string", "enum": ["barre", "linea", "torta"]},
            "titolo": {"type": "string"},
            "sql": {"type": "string", "description": "Una SELECT che restituisce due colonne: etichetta e valore."}},
            "required": ["tipo", "titolo", "sql"]}}},
]


class ErroreInterrogazione(Exception):
    """Interrogazione rifiutata o fallita: il testo torna al modello, che può correggersi."""


_AZIONI_PERMESSE = {sqlite3.SQLITE_SELECT, sqlite3.SQLITE_READ, sqlite3.SQLITE_FUNCTION, 33}  # 33 = SQLITE_RECURSIVE


def _solo_lettura(azione, *_):
    return sqlite3.SQLITE_OK if azione in _AZIONI_PERMESSE else sqlite3.SQLITE_DENY


class Dati:
    """La base dati delle fatture, aperta in sola lettura."""

    def __init__(self, file_db, righe_massime=200, secondi=5):
        self.file_db = Path(file_db)
        self.righe_massime = righe_massime
        self.secondi = secondi

    def _apri(self):
        con = sqlite3.connect(f"file:{self.file_db}?mode=ro", uri=True)
        con.execute("PRAGMA query_only = ON")
        return con

    def interroga(self, sql: str, righe_massime: int | None = None) -> dict:
        testo = (sql or "").strip().rstrip(";").strip()
        if not re.match(r"(?is)^\s*(select|with)\b", testo):
            raise ErroreInterrogazione("Sono permesse solo interrogazioni di lettura: una SELECT.")
        limite = righe_massime or self.righe_massime
        con = self._apri()
        scadenza = time.monotonic() + self.secondi
        con.set_progress_handler(lambda: 1 if time.monotonic() > scadenza else 0, 5000)
        con.set_authorizer(_solo_lettura)
        try:
            cur = con.execute(testo)
            righe = cur.fetchmany(limite + 1)
            colonne = [c[0] for c in cur.description or []]
        except sqlite3.Warning as e:
            raise ErroreInterrogazione("Una sola interrogazione alla volta.") from e
        except sqlite3.DatabaseError as e:
            msg = str(e)
            if "interrupted" in msg:
                msg = f"Interrogazione troppo lenta: fermata dopo {self.secondi} secondi."
            elif "not authorized" in msg or "readonly" in msg:
                msg = "Sono permesse solo interrogazioni di lettura: una SELECT."
            raise ErroreInterrogazione(f"Errore: {msg}") from e
        finally:
            con.close()
        pulite = [[round(v, 6) if isinstance(v, float) else v for v in r] for r in righe[:limite]]
        return {"colonne": colonne, "righe": pulite, "numero_righe": len(pulite), "troncato": len(righe) > limite}

    def struttura(self) -> dict:
        con = self._apri()
        try:
            lista = lambda sql: [r[0] for r in con.execute(sql)]
            periodo = con.execute("SELECT MIN(data), MAX(data) FROM fatture_valide").fetchone()
            return {
                "tabelle": COLONNE,
                "convenzioni": CONVENZIONI,
                "periodo": {"dal": periodo[0], "al": periodo[1]},
                "categorie": lista("SELECT DISTINCT categoria FROM fatture_valide ORDER BY 1"),
                "fornitori": [f"{f} ({c}; {co}, {p})" for f, c, co, p in con.execute(
                    "SELECT DISTINCT fornitore, categoria, comune, provincia FROM fatture_valide ORDER BY 1")],
                "articoli": [f"{a} [{u or 'senza unità'}] – {f}" for a, u, f in con.execute(
                    "SELECT DISTINCT articolo, unita, fornitore FROM righe_valide ORDER BY fornitore, articolo")],
                "colori_smalti": lista("SELECT DISTINCT variante FROM righe_valide WHERE variante IS NOT NULL ORDER BY 1"),
            }
        finally:
            con.close()

    def analisi(self, impostazioni: dict | None = None) -> dict:
        con = self._apri()
        try:
            return regole.analisi(con, impostazioni)
        finally:
            con.close()


def in_testo(valore) -> str:
    return json.dumps(valore, ensure_ascii=False, default=str)
