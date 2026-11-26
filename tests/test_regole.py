"""Le quattro regole trovano le quattro storie con le cifre attese."""
import pytest

from app import regole

IMPOSTAZIONI = {"categorie_fuori_totale": ["Energia e acqua"]}


def test_doppioni(db, attese):
    [caso] = regole.doppioni(db)
    atteso = attese["doppione"][0]
    for chiave in ("fornitore", "numero", "data", "imponibile", "totale", "file_doppio", "file_originale"):
        assert caso[chiave] == atteso[chiave]
    assert caso["imponibile"] == 1331.50


def test_aumenti(db, attese):
    casi = {c["articolo"]: c for c in regole.aumenti(db)}
    # con il filtro sulle unità di misura le commissioni sulle carte non escono
    assert set(casi) == {"Cera depilatoria liposolubile barattolo 800 ml", "Crema massaggio neutra 1 l", "Energia elettrica – consumo"}
    for atteso in attese["aumenti"]["articoli"]:
        caso = casi[atteso["articolo"]]
        assert caso["prezzo_iniziale"] == atteso["prezzo_iniziale"]
        assert caso["prezzo_finale"] == atteso["prezzo_finale"]
        assert caso["aumento_percento"] == atteso["aumento_percento"]
        assert caso["numero_ritocchi"] == atteso["numero_aumenti"]
        assert caso["quantita"] == atteso["pezzi"]
        assert caso["maggior_costo"] == atteso["maggior_costo"]
        assert caso["maggior_costo_annuo"] == atteso["maggior_costo_annuo_a_prezzo_finale"]
    luce = casi["Energia elettrica – consumo"]
    assert luce["aumento_percento"] == attese["energia"]["aumento_percento"] == 26.4
    assert luce["maggior_costo"] == attese["energia"]["maggior_costo_da_cambio_prezzo"] == 377.44
    assert luce["primo_mese_aumento"] == attese["energia"]["primo_mese_nuovo_prezzo"]
    assert luce["quantita"] == attese["energia"]["kwh_totali"]


def test_prezzi_diversi(db, attese):
    [caso] = regole.prezzi_diversi(db)
    basso, alto = attese["gel"]["dettaglio"]
    assert (caso["fornitore_conveniente"], caso["prezzo_basso"]) == (basso["fornitore"], basso["prezzo"])
    assert (caso["fornitore_caro"], caso["prezzo_alto"], caso["pezzi_al_prezzo_alto"]) == (alto["fornitore"], alto["prezzo"], alto["pezzi"])
    assert caso["differenza_percento"] == attese["gel"]["differenza_percento"]
    assert caso["risparmio_possibile"] == attese["gel"]["risparmio_possibile"] == 107.50


def test_canoni_dopo_la_fine(db, attese):
    [caso] = regole.canoni_dopo_fine(db)
    atteso = attese["pressoterapia"]
    assert caso["fornitore"] == atteso["fornitore"]
    assert caso["data_fine"] == atteso["data_ritiro"]
    assert caso["canoni_dopo_la_fine"] == atteso["canoni_dopo_il_ritiro"] == 4
    assert caso["mesi"] == atteso["mesi"]
    assert caso["importo_non_dovuto"] == atteso["importo_non_dovuto"] == 1040.00


@pytest.mark.parametrize("giro", range(10))
def test_totale_recuperabile_dieci_volte_su_dieci(db, attese, giro):
    a = regole.analisi(db, IMPOSTAZIONI)
    assert a["cose_trovate"] == 4
    assert sorted(v["importo"] for v in a["voci_recuperabili"]) == [107.50, 254.66, 1040.00, 1331.50]
    assert a["recuperabile_totale"] == attese["recuperabile_totale_imponibile"] == 2733.66
    futuro = {f["titolo"]: f for f in a["aumenti_che_pesano_sul_futuro"]}
    assert futuro["Prodotti rincarati"]["importo_annuo"] == attese["aumenti"]["maggior_costo_annuo_a_prezzi_finali"] == 603.93
    assert futuro["Energia elettrica – consumo"]["importo_annuo"] == 935.76


def test_panoramica(db, attese):
    p = regole.panoramica(db)
    assert p["spesa_totale"] == attese["spesa_totale_imponibile"]
    assert p["media_mensile"] == 5650.71
    assert p["categorie"] == attese["spesa_per_categoria"]
    assert p["mese_piu_caro"] == attese["mese_piu_caro"]
    assert p["mese_meno_caro"] == attese["mese_meno_caro"]
