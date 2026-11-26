"""Configurazione: legge config.toml e sceglie il profilo di modello.

Modulo volutamente isolato: in futuro può finire in una cartella comune alle due demo.
"""
import os
import tomllib
from pathlib import Path

RADICE = Path(__file__).resolve().parent.parent
LAVORO = RADICE / "lavoro"
REGISTRAZIONI = RADICE / "registrazioni"


def carica_config(percorso: Path | None = None) -> dict:
    with open(percorso or RADICE / "config.toml", "rb") as f:
        cfg = tomllib.load(f)
    cfg.setdefault("analisi", {})
    cfg.setdefault("pagina", {})
    cfg.setdefault("modello", {})
    return cfg


def profilo_attivo(cfg: dict) -> dict:
    """Il profilo indicato in config.toml, o quello forzato con la variabile PROFILO."""
    voluto = os.environ.get("PROFILO") or cfg["modello"].get("profilo_iniziale")
    for p in cfg.get("profili", []):
        if p["id"] == voluto:
            return p
    raise ValueError(f"Profilo di modello sconosciuto: {voluto!r}. Controlla config.toml.")


def chiave_del_profilo(profilo: dict) -> str:
    if "chiave_env" in profilo:
        return os.environ.get(profilo["chiave_env"], "")
    return profilo.get("chiave", "")


def file_fornitori(cfg: dict) -> Path:
    return RADICE / cfg.get("dati", {}).get("fornitori", "contesto/dati/fornitori.csv")


def prompt_sistema(cfg: dict, struttura: str) -> str:
    testo = (RADICE / "prompt_sistema.txt").read_text(encoding="utf-8")
    imp = cfg["impresa"]
    return (testo.replace("{nome}", imp["nome"])
                 .replace("{descrizione}", imp.get("descrizione", ""))
                 .replace("{titolare}", imp.get("titolare", "chi la gestisce"))
                 .replace("{struttura}", struttura))
