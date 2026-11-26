"""Caricamento: i 196 file diventano i numeri di contesto/dati/risposte_attese.json."""


def test_numeri_del_caricamento(caricato, attese):
    _, n = caricato
    assert n["file"] == attese["file_caricati"] == 196
    assert n["fatture_valide"] == attese["fatture_valide"] == 195
    assert n["doppioni"] == 1
    assert n["fornitori"] == attese["fornitori"] == 19
    assert n["righe"] == 500
    assert n["categorie"] == len(attese["spesa_per_categoria"]) == 16
    assert n["imponibile"] == attese["spesa_totale_imponibile"] == 67808.52
    assert n["periodo"] == attese["periodo"]
    assert n["scartati"] == []


def test_totali(db, attese):
    imponibile, iva, totale = db.execute("SELECT SUM(imponibile), SUM(iva), SUM(totale) FROM fatture_valide").fetchone()
    assert round(imponibile, 2) == attese["spesa_totale_imponibile"]
    assert round(iva, 2) == attese["iva_totale"]
    assert round(totale, 2) == attese["totale_con_iva"]


def test_spesa_per_categoria(db, attese):
    trovate = {c: round(s, 2) for c, s in db.execute("SELECT categoria, SUM(imponibile) FROM fatture_valide GROUP BY 1")}
    assert trovate == {c["categoria"]: c["spesa"] for c in attese["spesa_per_categoria"]}


def test_spesa_per_mese(db, attese):
    trovati = [{"mese": m, "spesa": round(s, 2)} for m, s in db.execute(
        "SELECT mese, SUM(imponibile) FROM fatture_valide GROUP BY 1 ORDER BY 1")]
    assert trovati == attese["spesa_per_mese"]


def test_nota_di_credito_col_segno_meno(db, attese):
    numero, data, imponibile = db.execute("SELECT numero, data, imponibile FROM fatture_valide WHERE tipo_documento = 'TD04'").fetchone()
    assert [numero, data, imponibile] == attese["natale"]["nota_di_credito"]
    assert db.execute("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'Reso cofanetto%'").fetchone()[0] == -8


def test_variante_solo_per_gli_smalti(db, attese):
    colori = [{"colore": c, "boccette": n} for c, n in db.execute(
        "SELECT variante, SUM(quantita) n FROM righe_valide WHERE articolo LIKE 'Smalto%' GROUP BY 1 ORDER BY n DESC")]
    assert colori == attese["smalti"]["per_colore"]
    assert db.execute("SELECT COUNT(*) FROM righe WHERE variante IS NOT NULL AND articolo NOT LIKE 'Smalto%'").fetchone()[0] == 0


def test_doppione_marcato_non_cancellato(db):
    assert db.execute("SELECT COUNT(*) FROM fatture").fetchone()[0] == 196
    assert db.execute("SELECT COUNT(*) FROM righe").fetchone()[0] == 504
    assert db.execute("SELECT file FROM fatture WHERE doppione = 1").fetchall() == [("IT09999000117_00002.xml",)]
