"""La pagina "Come funziona": lo schema si costruisce con e senza fatture, e la chiave non compare mai."""
import json

from app import regole, schema
from app.config import carica_config
from app.strumenti import STRUMENTI


def test_nome_del_modello():
    assert schema.nome_modello("anthropic:claude@sonnet-5.5") == "Claude Sonnet 5.5"
    assert schema.nome_modello("anthropic:claude@haiku-5.5") == "Claude Haiku 5.5"
    assert schema.nome_modello("gemma4:26b") == "gemma4:26b"


def test_schema_senza_fatture(tmp_path, monkeypatch):
    monkeypatch.setenv("CHIAVE_FRONTIERA", "segreta-da-non-mostrare")
    d = schema.descrivi(carica_config(), {"caricato": False}, tmp_path / "manca.db", None)
    assert set(d["parti"]) >= {"fatture", "basedati", "regole", "modello", "strumenti", "controllo", "risposta"}
    assert d["parti"]["fatture"]["riga"] == "nessun file"
    assert "segreta" not in json.dumps(d, ensure_ascii=False)
    assert ["Chiave", "presente"] in d["parti"]["modello"]["voci"]
    # ogni strumento ha la sua parte, con il nome con cui lo chiama il modello
    for s in STRUMENTI:
        parte = d["parti"]["t_" + s["function"]["name"]]
        assert ["Nome per il modello", s["function"]["name"]] in parte["voci"]
        assert json.loads(parte["tecnici"][0]["testo"]) == s
    assert not {"registro", "prove", "configurazione"} & set(d["parti"])


def test_schema_con_fatture(caricato, db):
    file_db, numeri = caricato
    stato = {"caricato": True, "statistiche": numeri, "analisi": None}
    a = regole.analisi(db, carica_config()["analisi"])
    d = schema.descrivi(carica_config(), stato, file_db, a)
    assert d["parti"]["fatture"]["riga"] == "196 file"
    assert d["parti"]["basedati"]["riga"] == "195 fatture"
    assert d["parti"]["regole"]["riga"] == "4 cose trovate"
    assert ["Totale", "2.733,66 €"] in d["parti"]["regole"]["voci"]
