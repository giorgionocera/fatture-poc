"""Controllo delle cifre: passa quello che sta nei risultati, si ferma quello che non c'è."""
from app import cifre

RISULTATO = {"colonne": ["categoria", "spesa", "quota", "mese", "kwh", "prezzo"],
             "righe": [["Affitto", 16800.0, 24.7753, "2026-08", 16710.0, 0.268]]}


def ok(testo, risultati=(RISULTATO,), altri=()):
    return cifre.non_verificate(testo, list(risultati), list(altri)) == []


def test_formati_italiani():
    assert ok("L'affitto pesa 16.800,00 €, il 24,8% della spesa.")
    assert ok("Sono 16.710 kWh a 0,268 € l'uno, il mese più caro è agosto 2026.")
    assert ok("16800 euro, cioè 16.800 €")


def test_cifra_inventata():
    assert cifre.non_verificate("L'affitto pesa 17.500,00 €.", [RISULTATO]) == ["17.500,00"]
    assert cifre.non_verificate("È il 31% della spesa.", [RISULTATO]) == ["31"]
    assert not ok("Circa 16.900 €")


def test_arrotondamento_ma_non_troppo():
    assert ok("il 24,78%") and ok("il 25%")
    assert not ok("il 24,5%")


def test_date_e_numeri_dentro_i_testi():
    r = {"colonne": ["fornitore", "numero", "data", "imponibile", "descrizione"],
         "righe": [["Dermovita Cosmetici S.p.A.", "2025-330", "2025-11-11", 1331.5, "Capsule caffè conf. 100 pz"]]}
    assert ok("La fattura 2025-330 dell'11/11/2025, 1.331,50 €, è presente due volte.", [r])
    assert ok("Confezioni da 100 capsule.", [r])
    assert not ok("La fattura del 12/11/2025.", [r])


def test_note_di_credito_senza_segno():
    assert ok("Una nota di credito da 176,00 € per 8 cofanetti.", [{"colonne": ["imponibile", "pezzi"], "righe": [[-176.0, -8.0]]}])


def test_numero_di_righe():
    r = {"colonne": ["fornitore"], "righe": [["a"], ["b"], ["c"], ["d"], ["e"], ["f"]]}
    assert ok("6 fornitori vogliono il pagamento subito.", [r])
    assert not ok("7 fornitori vogliono il pagamento subito.", [r])


def test_numeri_della_domanda_e_dell_interrogazione():
    r = {"colonne": ["confezioni", "guanti"], "righe": [[93.0, 9300.0]]}
    assert not ok("93 confezioni da 100: 9.300 guanti.", [r])
    assert ok("93 confezioni da 100: 9.300 guanti.", [r], ["SELECT SUM(quantita), SUM(quantita) * 100 FROM righe_valide"])


def test_frazione_come_percentuale():
    assert ok("Il 52,4% della spesa.", [{"colonne": ["quota"], "righe": [[0.5243]]}])


def test_senza_risultati_nessuna_cifra_passa():
    assert not ok("Hai speso 5.000,00 €.", [])
    assert ok("Nelle fatture ci sono solo gli acquisti: il fatturato non c'è.", [])
