"""Il server della pagina: caricamento, prima analisi, domande libere, reset."""
import asyncio
import json
import shutil
import sqlite3
import uuid
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles

from . import analisi as prima_analisi
from . import caricamento
from .agente import Agente, per_la_storia
from .config import LAVORO, carica_config, file_fornitori
from .modello import Modello
from .registro import Registro
from .strumenti import Dati

STATICI = Path(__file__).parent / "static"
FILE_DB = LAVORO / "fatture.db"
FILE_STATO = LAVORO / "stato.json"
CARTELLA_FATTURE = LAVORO / "fatture"

cfg = carica_config()
registro = Registro()
app = FastAPI(docs_url=None, redoc_url=None)
app.mount("/static", StaticFiles(directory=STATICI), name="static")
occupato = asyncio.Lock()


def stato_iniziale() -> dict:
    return {"generazione": uuid.uuid4().hex[:8], "caricato": False, "statistiche": None, "fatture": [],
            "analisi": None, "schede": []}


def leggi_stato() -> dict:
    if FILE_STATO.exists() and FILE_DB.exists():
        try:
            return json.loads(FILE_STATO.read_text(encoding="utf-8"))
        except ValueError:
            pass
    return stato_iniziale()


stato = leggi_stato()
_agente: Agente | None = None


def salva():
    LAVORO.mkdir(parents=True, exist_ok=True)
    FILE_STATO.write_text(json.dumps(stato, ensure_ascii=False), encoding="utf-8")


def agente() -> Agente:
    global _agente
    if _agente is None:
        m = cfg["modello"]
        dati = Dati(FILE_DB, m.get("righe_massime", 200), m.get("secondi_interrogazione", 5))
        _agente = Agente(cfg, Modello(cfg), dati, registro)
    return _agente


def versione_pagina() -> str:
    return str(max(int(f.stat().st_mtime) for f in STATICI.glob("*.*")))


@app.get("/")
def pagina():
    return FileResponse(STATICI / "index.html", headers={"Cache-Control": "no-store"})


@app.get("/api/stato")
def leggi():
    imp = cfg["impresa"]
    return JSONResponse({**stato, "versione": versione_pagina(), "pagina": cfg["pagina"],
                         "impresa": {k: imp.get(k) for k in ("nome", "sigla", "attivita", "dicitura", "tema")}},
                        headers={"Cache-Control": "no-store"})


@app.post("/api/carica")
async def carica(richiesta: Request):
    """Riceve i file della cartella trascinata e costruisce la base dati. Nessun modello coinvolto."""
    global stato, _agente
    corpo = await richiesta.json()
    xml = [f for f in corpo.get("file", []) if str(f.get("nome", "")).lower().endswith(".xml")]
    if not xml:
        return JSONResponse({"errore": "In questa cartella non ci sono fatture elettroniche (file .xml)."}, status_code=400)
    async with occupato:
        shutil.rmtree(CARTELLA_FATTURE, ignore_errors=True)
        CARTELLA_FATTURE.mkdir(parents=True)
        for f in xml:
            (CARTELLA_FATTURE / Path(f["nome"]).name).write_text(f["testo"], encoding="utf-8")
        numeri = await asyncio.to_thread(caricamento.carica, CARTELLA_FATTURE, file_fornitori(cfg), FILE_DB)
        if not numeri["file"]:
            return JSONResponse({"errore": "Non sono riuscito a leggere nessuna fattura da questa cartella."}, status_code=400)
        db = sqlite3.connect(f"file:{FILE_DB}?mode=ro", uri=True)
        elenco = caricamento.elenco_fatture(db)
        db.close()
        _agente = None
        stato = {**stato_iniziale(), "caricato": True, "statistiche": numeri, "fatture": elenco}
        salva()
        registro.scrivi("caricamento", **numeri)
    return {"statistiche": numeri, "fatture": elenco}


@app.post("/api/analisi")
async def analizza(richiesta: Request):
    """Prima analisi: quattro regole fisse, tre schede. Il modello scrive solo le frasi."""
    corpo = await richiesta.json()
    if not stato["caricato"]:
        return JSONResponse({"errore": "Prima servono le fatture."}, status_code=400)
    async with occupato:
        ag = agente()
        esito = await prima_analisi.esegui(ag.modello, cfg, ag.analisi(), bool(corpo.get("replay")), registro)
        stato["analisi"] = esito
        stato["schede"] = []
        salva()
    return esito


@app.post("/api/domanda")
async def domanda(richiesta: Request):
    """Una domanda libera. Risponde con una riga JSON per ogni passo, l'ultima è la scheda."""
    corpo = await richiesta.json()
    testo = str(corpo.get("testo", "")).strip()[:500]
    if not testo:
        return JSONResponse({"errore": "Scrivi una domanda."}, status_code=400)
    if not stato["caricato"]:
        return JSONResponse({"errore": "Prima servono le fatture: trascina la cartella a sinistra."}, status_code=400)

    async def flusso():
        coda: asyncio.Queue = asyncio.Queue()
        async with occupato:
            storia = per_la_storia(stato["schede"], cfg["modello"].get("domande_ricordate", 4))
            compito = asyncio.create_task(agente().rispondi(testo, storia, lambda t: coda.put_nowait(t)))
            while not compito.done() or not coda.empty():
                try:
                    passo = await asyncio.wait_for(coda.get(), timeout=0.2)
                    yield json.dumps({"tipo": "passo", "testo": passo}, ensure_ascii=False) + "\n"
                except asyncio.TimeoutError:
                    continue
            try:
                scheda = compito.result()
            except Exception as e:  # non deve mai restare una scheda appesa sul palco
                registro.scrivi("errore", domanda=testo, errore=repr(e))
                scheda = {"domanda": testo, "esito": "errore", "testo": "Qualcosa è andato storto. Riprova o cambia domanda.",
                          "cifra": None, "grafico": None, "come": {"passi": [], "fatture": None}, "interrogazioni": []}
            stato["schede"].append(scheda)
            salva()
            yield json.dumps({"tipo": "scheda", "scheda": scheda}, ensure_ascii=False) + "\n"

    return StreamingResponse(flusso(), media_type="application/x-ndjson", headers={"Cache-Control": "no-store"})


@app.post("/api/reset")
async def reset():
    """Riporta l'applicazione allo stato iniziale, senza fatture caricate. Il registro resta."""
    global stato, _agente
    async with occupato:
        shutil.rmtree(CARTELLA_FATTURE, ignore_errors=True)
        FILE_DB.unlink(missing_ok=True)
        FILE_STATO.unlink(missing_ok=True)
        _agente = None
        stato = stato_iniziale()
        registro.scrivi("reset")
    return {"ok": True}
