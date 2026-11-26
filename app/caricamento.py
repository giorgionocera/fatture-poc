"""Caricamento: legge una cartella di fatture elettroniche XML (FatturaPA) e crea la base dati SQLite.

Stesse convenzioni di contesto/strumenti/carica_fatture.py, su cui sono calcolati i numeri attesi:
 - spesa = imponibile, IVA esclusa;
 - importi e quantità delle note di credito (TD04) col segno meno;
 - un file con stesso fornitore, numero, data e totale di uno già caricato è marcato doppione = 1;
 - le viste fatture_valide e righe_valide escludono i doppioni.
Nessun modello coinvolto.
"""
import csv
import sqlite3
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

SCHEMA = """
CREATE TABLE fatture (id INTEGER PRIMARY KEY, file TEXT, fornitore TEXT, partita_iva TEXT, comune TEXT, provincia TEXT,
  regione TEXT, categoria TEXT, tipo_documento TEXT, numero TEXT, data TEXT, mese TEXT, imponibile REAL, iva REAL, totale REAL,
  scadenza TEXT, giorni_pagamento INTEGER, causale TEXT, doppione INTEGER DEFAULT 0);
CREATE TABLE righe (id INTEGER PRIMARY KEY, fattura_id INTEGER, fornitore TEXT, categoria TEXT, data TEXT, mese TEXT,
  descrizione TEXT, articolo TEXT, variante TEXT, quantita REAL, unita TEXT, prezzo_unitario REAL, importo REAL,
  aliquota_iva REAL, doppione INTEGER DEFAULT 0);
CREATE VIEW fatture_valide AS SELECT * FROM fatture WHERE doppione = 0;
CREATE VIEW righe_valide AS SELECT * FROM righe WHERE doppione = 0;
CREATE INDEX righe_fattura ON righe (fattura_id);
"""


def _testo(nodo, percorso, default=None):
    el = nodo.find(percorso) if nodo is not None else None
    return el.text.strip() if el is not None and el.text else default


def carica(cartella, file_fornitori, file_db) -> dict:
    """Crea da capo la base dati e restituisce i numeri del caricamento."""
    with open(file_fornitori, encoding="utf-8") as f:
        anagrafica = {r["partita_iva"]: r for r in csv.DictReader(f)}
    file_db = Path(file_db)
    file_db.parent.mkdir(parents=True, exist_ok=True)
    file_db.unlink(missing_ok=True)
    db = sqlite3.connect(file_db)
    db.executescript(SCHEMA)
    viste, scartati = set(), []
    for f in sorted(Path(cartella).glob("*.xml")):
        try:
            radice = ET.parse(f).getroot()
            _carica_file(db, f.name, radice, anagrafica, viste)
        except (ET.ParseError, AttributeError, TypeError, ValueError):
            scartati.append(f.name)
    db.commit()
    numeri = statistiche(db)
    numeri["scartati"] = scartati
    db.close()
    return numeri


def _carica_file(db, nome_file, radice, anagrafica, viste):
    ced = radice.find("FatturaElettronicaHeader/CedentePrestatore")
    piva = _testo(ced, "DatiAnagrafici/IdFiscaleIVA/IdCodice")
    nome = _testo(ced, "DatiAnagrafici/Anagrafica/Denominazione")
    a = anagrafica.get(piva, {})
    categoria = a.get("categoria", "Altro")
    for corpo in radice.findall("FatturaElettronicaBody"):
        gen = corpo.find("DatiGenerali/DatiGeneraliDocumento")
        tipo, numero, data = _testo(gen, "TipoDocumento"), _testo(gen, "Numero"), _testo(gen, "Data")
        segno = -1 if tipo == "TD04" else 1
        riepiloghi = corpo.findall("DatiBeniServizi/DatiRiepilogo")
        imponibile = sum(float(_testo(r, "ImponibileImporto")) for r in riepiloghi) * segno
        iva = sum(float(_testo(r, "Imposta")) for r in riepiloghi) * segno
        totale = float(_testo(gen, "ImportoTotaleDocumento")) * segno
        scadenza = _testo(corpo, "DatiPagamento/DettaglioPagamento/DataScadenzaPagamento")
        giorni = (date.fromisoformat(scadenza) - date.fromisoformat(data)).days if scadenza else None
        chiave = (piva, numero, data, round(totale, 2))
        doppione = 1 if chiave in viste else 0
        viste.add(chiave)
        cur = db.execute(
            "INSERT INTO fatture (file,fornitore,partita_iva,comune,provincia,regione,categoria,tipo_documento,numero,"
            "data,mese,imponibile,iva,totale,scadenza,giorni_pagamento,causale,doppione) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (nome_file, nome, piva, _testo(ced, "Sede/Comune"), _testo(ced, "Sede/Provincia"), a.get("regione"),
             categoria, tipo, numero, data, data[:7], round(imponibile, 2), round(iva, 2), round(totale, 2),
             scadenza, giorni, _testo(gen, "Causale"), doppione))
        for r in corpo.findall("DatiBeniServizi/DettaglioLinee"):
            descr = _testo(r, "Descrizione", "")
            articolo, _, variante = descr.partition(" – ")
            if not articolo.startswith("Smalto"):  # solo gli smalti hanno il colore come variante
                articolo, variante = descr, ""
            db.execute(
                "INSERT INTO righe (fattura_id,fornitore,categoria,data,mese,descrizione,articolo,variante,quantita,"
                "unita,prezzo_unitario,importo,aliquota_iva,doppione) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (cur.lastrowid, nome, categoria, data, data[:7], descr, articolo, variante or None,
                 float(_testo(r, "Quantita", "1")) * segno, _testo(r, "UnitaMisura"),
                 float(_testo(r, "PrezzoUnitario")), float(_testo(r, "PrezzoTotale")) * segno,
                 float(_testo(r, "AliquotaIVA")), doppione))


def statistiche(db) -> dict:
    uno = lambda sql: db.execute(sql).fetchone()[0]
    return {
        "file": uno("SELECT COUNT(*) FROM fatture"),
        "fatture_valide": uno("SELECT COUNT(*) FROM fatture_valide"),
        "doppioni": uno("SELECT COUNT(*) FROM fatture WHERE doppione = 1"),
        "fornitori": uno("SELECT COUNT(DISTINCT partita_iva) FROM fatture"),
        "righe": uno("SELECT COUNT(*) FROM righe_valide"),
        "categorie": uno("SELECT COUNT(DISTINCT categoria) FROM fatture_valide"),
        "imponibile": round(uno("SELECT COALESCE(SUM(imponibile), 0) FROM fatture_valide"), 2),
        "periodo": [uno("SELECT MIN(data) FROM fatture"), uno("SELECT MAX(data) FROM fatture")],
    }


def elenco_fatture(db) -> list[dict]:
    """L'elenco che scorre nella zona di sinistra, dalla più vecchia."""
    righe = db.execute("SELECT id, file, fornitore, numero, data, imponibile, tipo_documento, doppione, categoria "
                       "FROM fatture ORDER BY data, id").fetchall()
    chiavi = ["id", "file", "fornitore", "numero", "data", "imponibile", "tipo", "doppione", "categoria"]
    return [dict(zip(chiavi, r)) for r in righe]


def leggi_fattura(percorso) -> dict:
    """Una fattura XML in forma leggibile, così com'è scritta nel file (senza cambi di segno)."""
    radice = ET.parse(percorso).getroot()
    testata = radice.find("FatturaElettronicaHeader")
    corpo = radice.find("FatturaElettronicaBody")
    gen = corpo.find("DatiGenerali/DatiGeneraliDocumento")
    numero = lambda nodo, campo: float(_testo(nodo, campo)) if _testo(nodo, campo) is not None else None

    def soggetto(nodo):
        return {"nome": _testo(nodo, "DatiAnagrafici/Anagrafica/Denominazione"),
                "partita_iva": _testo(nodo, "DatiAnagrafici/IdFiscaleIVA/IdCodice"),
                "indirizzo": _testo(nodo, "Sede/Indirizzo"), "cap": _testo(nodo, "Sede/CAP"),
                "comune": _testo(nodo, "Sede/Comune"), "provincia": _testo(nodo, "Sede/Provincia")}

    pagamento = corpo.find("DatiPagamento")
    dettaglio = pagamento.find("DettaglioPagamento") if pagamento is not None else None
    return {
        "file": Path(percorso).name,
        "tipo": _testo(gen, "TipoDocumento"), "numero": _testo(gen, "Numero"), "data": _testo(gen, "Data"),
        "totale": numero(gen, "ImportoTotaleDocumento"), "causale": _testo(gen, "Causale"),
        "fornitore": soggetto(testata.find("CedentePrestatore")),
        "cliente": soggetto(testata.find("CessionarioCommittente")),
        "righe": [{"descrizione": _testo(r, "Descrizione"), "quantita": numero(r, "Quantita"), "unita": _testo(r, "UnitaMisura"),
                   "prezzo": numero(r, "PrezzoUnitario"), "importo": numero(r, "PrezzoTotale"), "aliquota": numero(r, "AliquotaIVA")}
                  for r in corpo.findall("DatiBeniServizi/DettaglioLinee")],
        "riepiloghi": [{"aliquota": numero(r, "AliquotaIVA"), "natura": _testo(r, "Natura"),
                        "imponibile": numero(r, "ImponibileImporto"), "imposta": numero(r, "Imposta")}
                       for r in corpo.findall("DatiBeniServizi/DatiRiepilogo")],
        "pagamento": None if dettaglio is None else {
            "modalita": _testo(dettaglio, "ModalitaPagamento"), "scadenza": _testo(dettaglio, "DataScadenzaPagamento"),
            "importo": numero(dettaglio, "ImportoPagamento")},
    }
