"""L'agente con un modello finto: ciclo degli strumenti, controllo delle cifre, limiti."""
import json

import pytest

from app.agente import Agente, cifra_principale
from app.config import carica_config

SQL_TOTALE = "SELECT ROUND(SUM(imponibile), 2) AS spesa FROM fatture_valide"


def chiama(nome, **argomenti):
    return {"role": "assistant", "content": "", "tool_calls": [
        {"id": "c1", "type": "function", "function": {"name": nome, "arguments": json.dumps(argomenti)}}]}


def dice(testo):
    return {"role": "assistant", "content": testo}


class ModelloFinto:
    nome = "finto"

    def __init__(self, *risposte):
        self.risposte = list(risposte)
        self.ricevuti = []

    async def chiedi(self, messaggi, strumenti=None):
        self.ricevuti.append(list(messaggi))
        return self.risposte.pop(0) if len(self.risposte) > 1 else self.risposte[0]


@pytest.fixture
def agente(dati):
    def crea(*risposte):
        return Agente(carica_config(), ModelloFinto(*risposte), dati)
    return crea


async def test_risposta_con_cifra_verificata(agente):
    passi = []
    a = agente(chiama("interroga", sql=SQL_TOTALE, cosa_cerco="tutte le fatture dell'anno"),
               dice("In tutto hai speso **67.808,52 €**, IVA esclusa."))
    s = await a.rispondi("Quanto ho speso in tutto?", su_passo=passi.append)
    assert s["esito"] == "ok"
    assert s["cifra"] == "67.808,52 €" and s["testo"] == "In tutto hai speso 67.808,52 €, IVA esclusa."
    assert passi == ["Sto guardando tutte le fatture dell'anno"]
    assert len(s["come"]["fatture"]) == 195 and s["come"]["totale"] == 67808.52
    assert s["interrogazioni"] == [SQL_TOTALE]


async def test_numero_inventato_non_va_a_schermo(agente):
    a = agente(chiama("interroga", sql=SQL_TOTALE, cosa_cerco="tutte le fatture"),
               dice("In tutto hai speso **71.250,00 €**."))
    s = await a.rispondi("Quanto ho speso in tutto?")
    assert s["esito"] == "solo_dati"
    assert "71.250" not in json.dumps(s, ensure_ascii=False)
    assert s["testo"] == "Ecco i dati, giudicate voi." and s["cifra"] is None
    assert s["tabella"]["righe"] == [[67808.52]]
    # al modello è stata chiesta una sola riscrittura
    assert sum("non compaiono nei risultati" in m["content"] for m in a.modello.ricevuti[-1] if m["role"] == "user") == 1


async def test_riscrittura_che_corregge(agente):
    a = agente(chiama("interroga", sql=SQL_TOTALE, cosa_cerco="tutte le fatture"),
               dice("Circa 70.000 €."), dice("Hai speso **67.808,52 €**."))
    s = await a.rispondi("Quanto ho speso in tutto?")
    assert s["esito"] == "ok" and s["cifra"] == "67.808,52 €"


async def test_cifra_a_memoria_senza_interrogazione(agente):
    s = await agente(dice("Hai speso 50.000,00 €.")).rispondi("Quanto ho speso?")
    assert s["esito"] == "limite" and "50.000" not in s["testo"]


async def test_fuori_dai_dati(agente):
    s = await agente(dice("Nelle fatture ricevute ci sono solo gli acquisti: il fatturato non c'è. Posso dirti quanto hai speso.")).rispondi("Quanto ho fatturato?")
    assert s["esito"] == "ok" and s["cifra"] is None and s["come"]["fatture"] is None


async def test_errore_torna_al_modello_che_si_corregge(agente):
    a = agente(chiama("interroga", sql="SELECT spesa FROM fatture_valide", cosa_cerco="la spesa"),
               chiama("interroga", sql=SQL_TOTALE, cosa_cerco="la spesa"), dice("**67.808,52 €** in tutto."))
    s = await a.rispondi("Quanto ho speso?")
    assert s["esito"] == "ok"
    assert "no such column" in a.modello.ricevuti[1][-1]["content"]


async def test_tre_interrogazioni_sbagliate_e_si_ferma(agente):
    a = agente(chiama("interroga", sql="SELECT nulla FROM niente", cosa_cerco="x"))
    s = await a.rispondi("Domanda impossibile")
    assert s["esito"] == "limite" and len(a.modello.ricevuti) == 3


async def test_modifica_rifiutata(agente, dati):
    a = agente(chiama("interroga", sql="DELETE FROM fatture", cosa_cerco="x"), dice("Non posso modificare le fatture."))
    await a.rispondi("Cancella tutte le fatture")
    assert "solo interrogazioni di lettura" in a.modello.ricevuti[1][-1]["content"]
    assert dati.interroga("SELECT COUNT(*) FROM fatture")["righe"] == [[196]]


async def test_limite_di_otto_passi(agente):
    a = agente(chiama("struttura_dati"))
    s = await a.rispondi("Gira a vuoto")
    assert s["esito"] == "limite" and len(a.modello.ricevuti) == 8


async def test_grafico_e_analisi_iniziale(agente):
    a = agente(chiama("analisi_iniziale"),
               chiama("mostra_grafico", tipo="linea", titolo="Spesa per mese",
                      sql="SELECT mese, ROUND(SUM(imponibile), 2) FROM fatture_valide GROUP BY 1 ORDER BY 1"),
               dice("La fattura 2025-330 di Dermovita, **1.331,50 €**, è arrivata due volte."))
    s = await a.rispondi("C'è qualcosa che pago due volte?")
    assert s["esito"] == "ok" and s["grafico"]["tipo"] == "linea" and len(s["grafico"]["punti"]) == 12


async def test_provenienza_dalla_prima_analisi(agente):
    a = agente(chiama("analisi_iniziale"), dice("La fattura 2025-330 di Dermovita Cosmetici, **1.331,50 €**, è presente due volte."))
    s = await a.rispondi("C'è qualcosa che pago due volte?")
    assert [f["file"] for f in s["come"]["fatture"]] == ["IT09999000117_00001.xml", "IT09999000117_00002.xml"]


def test_cifra_principale():
    assert cifra_principale("Hai comprato **314 boccette** per 2.166,60 €.") == ("314 boccette", "Hai comprato 314 boccette per 2.166,60 €.")
    assert cifra_principale("Hai speso 950,00 € in due corsi.")[0] == "950,00 €"
    assert cifra_principale("Il fatturato non c'è.") == (None, "Il fatturato non c'è.")


async def test_provenienza_dall_interrogazione_della_cifra_principale(agente):
    """Se l'agente guarda prima le capsule e poi tutto il fornitore, le fatture mostrate sono quelle delle capsule."""
    capsule = "SELECT ROUND(SUM(importo), 2) AS spesa FROM righe_valide WHERE articolo LIKE 'Capsule%'"
    fornitore = "SELECT ROUND(SUM(imponibile), 2) AS spesa FROM fatture_valide WHERE fornitore LIKE 'Caffè%'"
    a = agente(chiama("interroga", sql=capsule, cosa_cerco="le capsule di caffè"),
               chiama("interroga", sql=fornitore, cosa_cerco="tutto il fornitore del caffè"),
               dice("Per il caffè spendi **552,00 €**; dallo stesso fornitore compri in tutto 827,50 €."))
    s = await a.rispondi("Quanto spendo di caffè?")
    assert s["esito"] == "ok" and s["cifra"] == "552,00 €"
    assert s["come"]["totale"] == 552.00
