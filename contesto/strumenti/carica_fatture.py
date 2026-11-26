#!/usr/bin/env python3
"""Riferimento: legge una cartella di fatture elettroniche XML (FatturaPA) e crea un database SQLite.
Uso: python3 carica_fatture.py CARTELLA_FATTURE fornitori.csv fatture.db
Convenzioni (le stesse su cui sono calcolate le risposte attese):
 - gli importi delle note di credito (TD04) sono registrati col segno meno;
 - una fattura con stesso fornitore, numero, data e totale di una già caricata è marcata doppione=1;
 - le viste fatture_valide e righe_valide escludono i doppioni: le analisi si fanno su quelle;
 - "spesa" significa imponibile, IVA esclusa."""
import csv, sqlite3, sys
import xml.etree.ElementTree as ET
from datetime import date
from pathlib import Path

def testo(nodo, percorso, default=None):
    el = nodo.find(percorso)
    return el.text.strip() if el is not None and el.text else default

def carica(cartella, file_fornitori, file_db):
    anag = {r["partita_iva"]: r for r in csv.DictReader(open(file_fornitori, encoding="utf-8"))}
    Path(file_db).unlink(missing_ok=True)
    db = sqlite3.connect(file_db)
    db.executescript("""
    CREATE TABLE fatture (id INTEGER PRIMARY KEY, file TEXT, fornitore TEXT, partita_iva TEXT, comune TEXT, provincia TEXT,
      regione TEXT, categoria TEXT, tipo_documento TEXT, numero TEXT, data TEXT, mese TEXT, imponibile REAL, iva REAL, totale REAL,
      scadenza TEXT, giorni_pagamento INTEGER, causale TEXT, doppione INTEGER DEFAULT 0);
    CREATE TABLE righe (id INTEGER PRIMARY KEY, fattura_id INTEGER, fornitore TEXT, categoria TEXT, data TEXT, mese TEXT,
      descrizione TEXT, articolo TEXT, variante TEXT, quantita REAL, unita TEXT, prezzo_unitario REAL, importo REAL, aliquota_iva REAL, doppione INTEGER DEFAULT 0);
    CREATE VIEW fatture_valide AS SELECT * FROM fatture WHERE doppione = 0;
    CREATE VIEW righe_valide AS SELECT * FROM righe WHERE doppione = 0;
    """)
    viste = set()
    for f in sorted(Path(cartella).glob("*.xml")):
        radice = ET.parse(f).getroot()
        ced = radice.find("FatturaElettronicaHeader/CedentePrestatore")
        piva = testo(ced, "DatiAnagrafici/IdFiscaleIVA/IdCodice")
        nome = testo(ced, "DatiAnagrafici/Anagrafica/Denominazione")
        a = anag.get(piva, {})
        for corpo in radice.findall("FatturaElettronicaBody"):
            gen = corpo.find("DatiGenerali/DatiGeneraliDocumento")
            tipo, numero, data = testo(gen, "TipoDocumento"), testo(gen, "Numero"), testo(gen, "Data")
            segno = -1 if tipo == "TD04" else 1
            imponibile = sum(float(testo(r, "ImponibileImporto")) for r in corpo.findall("DatiBeniServizi/DatiRiepilogo")) * segno
            iva = sum(float(testo(r, "Imposta")) for r in corpo.findall("DatiBeniServizi/DatiRiepilogo")) * segno
            totale = float(testo(gen, "ImportoTotaleDocumento")) * segno
            scadenza = testo(corpo, "DatiPagamento/DettaglioPagamento/DataScadenzaPagamento")
            giorni = (date.fromisoformat(scadenza) - date.fromisoformat(data)).days if scadenza else None
            chiave = (piva, numero, data, round(totale, 2))
            doppione = 1 if chiave in viste else 0
            viste.add(chiave)
            cur = db.execute("INSERT INTO fatture (file,fornitore,partita_iva,comune,provincia,regione,categoria,tipo_documento,numero,data,mese,imponibile,iva,totale,scadenza,giorni_pagamento,causale,doppione) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                (f.name, nome, piva, testo(ced, "Sede/Comune"), testo(ced, "Sede/Provincia"), a.get("regione"), a.get("categoria", "Altro"),
                 tipo, numero, data, data[:7], round(imponibile, 2), round(iva, 2), round(totale, 2), scadenza, giorni, testo(gen, "Causale"), doppione))
            for r in corpo.findall("DatiBeniServizi/DettaglioLinee"):
                descr = testo(r, "Descrizione")
                articolo, _, variante = descr.partition(" – ")
                if not articolo.startswith("Smalto"):   # solo gli smalti hanno il colore come variante
                    articolo, variante = descr, ""
                db.execute("INSERT INTO righe (fattura_id,fornitore,categoria,data,mese,descrizione,articolo,variante,quantita,unita,prezzo_unitario,importo,aliquota_iva,doppione) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
                    (cur.lastrowid, nome, a.get("categoria", "Altro"), data, data[:7], descr, articolo, variante or None,
                     float(testo(r, "Quantita", "1")) * segno, testo(r, "UnitaMisura"), float(testo(r, "PrezzoUnitario")),
                     float(testo(r, "PrezzoTotale")) * segno, float(testo(r, "AliquotaIVA")), doppione))
    db.commit()
    return db

if __name__ == "__main__":
    db = carica(*sys.argv[1:4])
    print(db.execute("SELECT COUNT(*), SUM(doppione) FROM fatture").fetchone(), "fatture caricate (totale, doppioni)")
