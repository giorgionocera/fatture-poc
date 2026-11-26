"""Le quattro regole fisse della prima analisi. Nessun modello: solo conti sulle fatture.

Ogni regola restituisce i casi trovati con le cifre e le fatture da cui vengono.
"""
from collections import defaultdict

from .formato import nome_breve

SOGLIA = 5.0
PAROLE_FINE = ["ritiro", "fine noleggio", "disdetta", "cessazione"]
r2 = lambda x: round(x + 0.0, 2)


def _fattura(db, fattura_id, importo=None) -> dict:
    f = db.execute("SELECT fornitore, numero, data, imponibile, file FROM fatture WHERE id = ?", (fattura_id,)).fetchone()
    return {"fornitore": f[0], "numero": f[1], "data": f[2],
            "importo": r2(f[3] if importo is None else importo), "file": f[4]}


def doppioni(db) -> list[dict]:
    """File con stesso fornitore, numero, data e totale di uno già caricato."""
    casi = []
    for fid, fornitore, numero, data, imponibile, totale, file, piva in db.execute(
            "SELECT id, fornitore, numero, data, imponibile, totale, file, partita_iva FROM fatture WHERE doppione = 1 ORDER BY data"):
        originale = db.execute(
            "SELECT id, file FROM fatture WHERE doppione = 0 AND partita_iva = ? AND numero = ? AND data = ?",
            (piva, numero, data)).fetchone()
        casi.append({"fornitore": fornitore, "numero": numero, "data": data, "imponibile": r2(imponibile),
                     "totale": r2(totale), "file_doppio": file, "file_originale": originale[1],
                     "fatture": [_fattura(db, originale[0]), _fattura(db, fid)]})
    return casi


def aumenti(db, soglia=SOGLIA) -> list[dict]:
    """Stesso articolo e stesso fornitore, righe con unità di misura, prezzo finale più alto di quello iniziale."""
    serie = defaultdict(list)
    for fornitore, articolo, categoria, data, mese, prezzo, quantita, unita, fid in db.execute(
            "SELECT fornitore, articolo, categoria, data, mese, prezzo_unitario, quantita, unita, fattura_id "
            "FROM righe_valide WHERE unita IS NOT NULL AND unita <> '' AND quantita > 0 ORDER BY data, id"):
        serie[(fornitore, articolo)].append((data, mese, prezzo, quantita, unita, fid, categoria))
    casi = []
    for (fornitore, articolo), righe in serie.items():
        p0, p1 = righe[0][2], righe[-1][2]
        if p0 <= 0 or p1 < p0 * (1 + soglia / 100):
            continue
        pezzi = sum(r[3] for r in righe)
        ritocchi = sum(1 for a, b in zip(righe, righe[1:]) if b[2] != a[2])
        casi.append({
            "fornitore": fornitore, "articolo": articolo, "categoria": righe[0][6], "unita": righe[0][4],
            "prezzo_iniziale": p0, "prezzo_finale": p1, "aumento_percento": round(100 * (p1 / p0 - 1), 1),
            "numero_ritocchi": ritocchi, "quantita": pezzi,
            "primo_mese_aumento": next(r[1] for r in righe if r[2] != p0),
            "maggior_costo": r2(sum(r[3] * (r[2] - p0) for r in righe)),
            "maggior_costo_annuo": r2(pezzi * (p1 - p0)),
            "serie": [{"mese": r[1], "prezzo": r[2]} for r in righe],
            "fatture": [_fattura(db, r[5], r[3] * r[2]) for r in righe if r[2] != p0],
        })
    return sorted(casi, key=lambda c: (c["fornitore"], -c["maggior_costo"]))


def prezzi_diversi(db, soglia=SOGLIA) -> list[dict]:
    """Stesso articolo comprato da fornitori diversi, a prezzi che differiscono."""
    per_articolo = defaultdict(lambda: defaultdict(list))
    for articolo, fornitore, prezzo, quantita, fid in db.execute(
            "SELECT articolo, fornitore, prezzo_unitario, quantita, fattura_id FROM righe_valide "
            "WHERE unita IS NOT NULL AND unita <> '' AND quantita > 0 ORDER BY data, id"):
        per_articolo[articolo][fornitore].append((prezzo, quantita, fid))
    casi = []
    for articolo, fornitori in per_articolo.items():
        if len(fornitori) < 2:
            continue
        ultimo = {f: righe[-1][0] for f, righe in fornitori.items()}
        conveniente = min(ultimo, key=ultimo.get)
        basso = ultimo[conveniente]
        for fornitore, righe in fornitori.items():
            alto = ultimo[fornitore]
            if fornitore == conveniente or alto < basso * (1 + soglia / 100):
                continue
            care = [r for r in righe if r[0] > basso]
            casi.append({
                "articolo": articolo, "fornitore_conveniente": conveniente, "prezzo_basso": basso,
                "pezzi_al_prezzo_basso": sum(r[1] for r in fornitori[conveniente]),
                "fornitore_caro": fornitore, "prezzo_alto": alto,
                "differenza_percento": round(100 * (alto / basso - 1), 1),
                "pezzi_al_prezzo_alto": sum(r[1] for r in care),
                "risparmio_possibile": r2(sum(r[1] * (r[0] - basso) for r in care)),
                "fatture": [_fattura(db, r[2], r[0] * r[1]) for r in care],
            })
    return casi


def canoni_dopo_fine(db, parole=PAROLE_FINE) -> list[dict]:
    """Una riga che parla di ritiro o disdetta, seguita da canoni dello stesso fornitore in date successive."""
    dove = " OR ".join("LOWER(descrizione) LIKE ?" for _ in parole)
    casi = []
    for fornitore, data_fine, descrizione, fid in db.execute(
            f"SELECT fornitore, data, descrizione, fattura_id FROM righe_valide WHERE {dove} ORDER BY data",
            [f"%{p.lower()}%" for p in parole]).fetchall():
        prima = [r[0] for r in db.execute(
            "SELECT DISTINCT articolo FROM righe_valide WHERE fornitore = ? AND data <= ? AND LOWER(descrizione) LIKE '%canone%'",
            (fornitore, data_fine))]
        # se la riga di fine nomina il macchinario, vale solo il suo canone
        nominati = [a for a in prima if any(len(p) > 4 and p in descrizione.lower() for p in a.lower().split()[1:])]
        articoli = nominati or prima
        if not articoli:
            continue
        segni = ",".join("?" for _ in articoli)
        dopo = db.execute(
            f"SELECT mese, data, importo, fattura_id, articolo FROM righe_valide WHERE fornitore = ? AND data > ? "
            f"AND articolo IN ({segni}) ORDER BY data", (fornitore, data_fine, *articoli)).fetchall()
        if not dopo:
            continue
        casi.append({
            "fornitore": fornitore, "data_fine": data_fine, "riga_di_fine": descrizione,
            "articolo": dopo[0][4], "canoni_dopo_la_fine": len(dopo), "mesi": [d[0] for d in dopo],
            "canone": r2(dopo[0][2]), "importo_non_dovuto": r2(sum(d[2] for d in dopo)),
            "fatture": [_fattura(db, fid, 0)] + [_fattura(db, d[3], d[2]) for d in dopo],
        })
    return casi


def panoramica(db) -> dict:
    """Dove vanno i soldi: totali, categorie, mesi."""
    totale, iva, con_iva = db.execute("SELECT SUM(imponibile), SUM(iva), SUM(totale) FROM fatture_valide").fetchone()
    mesi = [{"mese": m, "spesa": r2(s)} for m, s in db.execute(
        "SELECT mese, SUM(imponibile) FROM fatture_valide GROUP BY 1 ORDER BY 1")]
    categorie = [{"categoria": c, "spesa": r2(s), "quota_percento": round(100 * s / totale, 1)} for c, s in db.execute(
        "SELECT categoria, SUM(imponibile) s FROM fatture_valide GROUP BY 1 ORDER BY s DESC")]
    return {
        "spesa_totale": r2(totale), "iva": r2(iva), "totale_con_iva": r2(con_iva),
        "media_mensile": r2(totale / len(mesi)), "numero_mesi": len(mesi),
        "fatture": db.execute("SELECT COUNT(*) FROM fatture_valide").fetchone()[0],
        "fornitori": db.execute("SELECT COUNT(DISTINCT partita_iva) FROM fatture_valide").fetchone()[0],
        "categorie": categorie, "mesi": mesi,
        "mese_piu_caro": max(mesi, key=lambda m: m["spesa"]), "mese_meno_caro": min(mesi, key=lambda m: m["spesa"]),
    }


def analisi(db, impostazioni: dict | None = None) -> dict:
    """Applica le quattro regole e compone le voci del totale recuperabile."""
    imp = impostazioni or {}
    fuori = set(imp.get("categorie_fuori_totale", []))
    d = doppioni(db)
    a = aumenti(db, imp.get("soglia_aumento_percento", SOGLIA))
    p = prezzi_diversi(db, imp.get("soglia_differenza_percento", SOGLIA))
    c = canoni_dopo_fine(db, imp.get("parole_fine_contratto", PAROLE_FINE))
    for caso in a:
        caso["nel_totale"] = caso["categoria"] not in fuori

    voci = []
    for caso in d:
        voci.append({"regola": "doppioni", "titolo": "Fattura doppia", "importo": caso["imponibile"],
                     "dettaglio": f"{nome_breve(caso['fornitore'])}, fattura {caso['numero']}"})
    for caso in c:
        voci.append({"regola": "canoni_dopo_fine", "titolo": "Canone dopo il ritiro", "importo": caso["importo_non_dovuto"],
                     "dettaglio": f"{nome_breve(caso['fornitore'])}, {caso['canoni_dopo_la_fine']} canoni"})
    per_fornitore = defaultdict(list)
    for caso in a:
        if caso["nel_totale"]:
            per_fornitore[caso["fornitore"]].append(caso)
    for fornitore, casi in per_fornitore.items():
        voci.append({"regola": "aumenti", "titolo": "Aumenti a piccoli passi",
                     "importo": r2(sum(x["maggior_costo"] for x in casi)),
                     "dettaglio": f"{nome_breve(fornitore)}, {len(casi)} articoli"})
    for caso in p:
        voci.append({"regola": "prezzi_diversi", "titolo": "Stesso articolo, due prezzi", "importo": caso["risparmio_possibile"],
                     "dettaglio": f"{caso['articolo']}"})

    futuro = []
    nel_totale = [x for x in a if x["nel_totale"]]
    if nel_totale:
        futuro.append({"titolo": "Prodotti rincarati", "importo_annuo": r2(sum(x["maggior_costo_annuo"] for x in nel_totale)),
                       "dettaglio": "in più ogni anno, ai prezzi di oggi"})
    for caso in a:
        if not caso["nel_totale"]:
            futuro.append({"titolo": caso["articolo"], "importo_annuo": r2(caso["maggior_costo_annuo"]),
                           "gia_pagato": caso["maggior_costo"], "dettaglio": "in più ogni anno, ai prezzi di oggi"})
    return {
        "panoramica": panoramica(db),
        "doppioni": d, "aumenti": a, "prezzi_diversi": p, "canoni_dopo_fine": c,
        "voci_recuperabili": voci, "cose_trovate": len(voci),
        "recuperabile_totale": r2(sum(v["importo"] for v in voci)),
        "aumenti_che_pesano_sul_futuro": futuro,
    }
