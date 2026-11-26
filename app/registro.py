"""Registro: ogni domanda, interrogazione e risultato finisce in lavoro/registro.jsonl, una riga per evento."""
import json
from datetime import datetime
from pathlib import Path

from .config import LAVORO


class Registro:
    def __init__(self, percorso: Path | None = None):
        self.percorso = percorso or LAVORO / "registro.jsonl"

    def scrivi(self, evento: str, **dati):
        self.percorso.parent.mkdir(parents=True, exist_ok=True)
        riga = {"quando": datetime.now().isoformat(timespec="seconds"), "evento": evento, **dati}
        with open(self.percorso, "a", encoding="utf-8") as f:
            f.write(json.dumps(riga, ensure_ascii=False, default=str) + "\n")
