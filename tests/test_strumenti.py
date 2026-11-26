"""Sola lettura, limiti dell'interrogazione, provenienza."""
import pytest

from app import provenienza
from app.strumenti import ErroreInterrogazione


def test_interroga_restituisce_le_righe(dati):
    r = dati.interroga("SELECT ROUND(SUM(imponibile), 2) AS spesa FROM fatture_valide")
    assert r["colonne"] == ["spesa"] and r["righe"] == [[67808.52]]


@pytest.mark.parametrize("sql", [
    "DELETE FROM fatture",
    "UPDATE fatture SET imponibile = 0",
    "DROP TABLE righe",
    "INSERT INTO fatture (file) VALUES ('x')",
    "SELECT 1; DELETE FROM fatture",
    "WITH x AS (SELECT 1) DELETE FROM fatture",
    "PRAGMA writable_schema = 1",
    "ATTACH DATABASE '/tmp/x.db' AS x",
    "CREATE TABLE x (a)",
])
def test_modifiche_rifiutate(dati, sql):
    with pytest.raises(ErroreInterrogazione):
        dati.interroga(sql)
    assert dati.interroga("SELECT COUNT(*) FROM fatture")["righe"] == [[196]]


def test_errore_leggibile_per_il_modello(dati):
    with pytest.raises(ErroreInterrogazione, match="colonna_inventata"):
        dati.interroga("SELECT colonna_inventata FROM fatture_valide")


def test_massimo_duecento_righe(dati):
    r = dati.interroga("SELECT * FROM righe_valide")
    assert r["numero_righe"] == 200 and r["troncato"] is True


def test_limite_di_tempo(caricato):
    from app.strumenti import Dati
    lento = Dati(caricato[0], secondi=0.2)
    with pytest.raises(ErroreInterrogazione, match="troppo lenta"):
        lento.interroga("WITH RECURSIVE c(x) AS (SELECT 1 UNION ALL SELECT x + 1 FROM c) SELECT COUNT(*) FROM c")


def test_struttura(dati):
    s = dati.struttura()
    assert len(s["categorie"]) == 16 and len(s["fornitori"]) == 19 and len(s["colori_smalti"]) == 10
    assert s["periodo"] == {"dal": "2025-11-01", "al": "2026-10-28"}


def test_provenienza_dalle_righe(dati):
    fatture = provenienza.fatture_coinvolte(
        dati, "SELECT SUM(quantita) AS boccette, ROUND(SUM(importo), 2) FROM righe_valide WHERE articolo LIKE 'Smalto%'")
    assert len(fatture) == 12 and {f["fornitore"] for f in fatture} == {"Nail Point Italia S.r.l."}
    assert round(sum(f["importo"] for f in fatture), 2) == 2166.60


def test_provenienza_dalle_fatture(dati):
    fatture = provenienza.fatture_coinvolte(
        dati, "SELECT ROUND(SUM(f.imponibile), 2) FROM fatture_valide f WHERE f.fornitore LIKE 'MedLaser%'")
    assert len(fatture) == 12 and round(sum(f["importo"] for f in fatture), 2) == 9144.00


def test_provenienza_con_interrogazione_annidata(dati):
    fatture = provenienza.fatture_coinvolte(dati, """
        WITH luce AS (SELECT mese, SUM(importo) AS spesa FROM righe_valide WHERE fornitore LIKE 'Luce%' GROUP BY mese)
        SELECT mese, spesa FROM luce ORDER BY spesa DESC LIMIT 1""")
    assert len(fatture) == 12 and round(sum(f["importo"] for f in fatture), 2) == 4375.96


def test_provenienza_illeggibile(dati):
    assert provenienza.fatture_coinvolte(dati, "SELECT 1") is None
