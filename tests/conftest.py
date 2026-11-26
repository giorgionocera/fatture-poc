import json
import sqlite3
from pathlib import Path

import pytest

from app import caricamento
from app.strumenti import Dati

RADICE = Path(__file__).resolve().parent.parent
DATI = RADICE / "contesto" / "dati"


@pytest.fixture(scope="session")
def attese():
    return json.loads((DATI / "risposte_attese.json").read_text(encoding="utf-8"))


@pytest.fixture(scope="session")
def caricato(tmp_path_factory):
    file_db = tmp_path_factory.mktemp("db") / "fatture.db"
    numeri = caricamento.carica(DATI / "fatture", DATI / "fornitori.csv", file_db)
    return file_db, numeri


@pytest.fixture
def db(caricato):
    con = sqlite3.connect(f"file:{caricato[0]}?mode=ro", uri=True)
    yield con
    con.close()


@pytest.fixture
def dati(caricato):
    return Dati(caricato[0])
