"""Collegamento al modello: protocollo compatibile OpenAI (chat completions con strumenti).

È l'unico modulo che fa chiamate di rete. Nessuna libreria del fornitore del modello.
Modulo volutamente isolato: in futuro può finire in una cartella comune alle due demo.
"""
import httpx

from .config import chiave_del_profilo, profilo_attivo


class ErroreModello(Exception):
    """Il modello non ha risposto o ha risposto in modo inutilizzabile."""


class Modello:
    def __init__(self, cfg: dict):
        self.profilo = profilo_attivo(cfg)
        self.impostazioni = cfg["modello"]
        self.chiave = chiave_del_profilo(self.profilo)

    @property
    def nome(self) -> str:
        return self.profilo["modello"]

    async def chiedi(self, messaggi: list[dict], strumenti: list[dict] | None = None) -> dict:
        """Manda la conversazione e restituisce il messaggio dell'assistente (content, tool_calls)."""
        if not self.chiave:
            raise ErroreModello(
                f"Manca la chiave del modello: scrivi {self.profilo.get('chiave_env', 'la chiave')} nel file .env e riavvia.")
        corpo = {"model": self.profilo["modello"], "messages": messaggi}
        if strumenti:
            corpo["tools"] = strumenti
        if self.profilo.get("invia_temperatura", True):
            corpo["temperature"] = self.impostazioni.get("temperatura", 0)
        corpo.update(self.profilo.get("parametri", {}))   # parametri in più del profilo, passati così come sono
        attesa = self.impostazioni.get("attesa_massima_secondi", 60)
        try:
            async with httpx.AsyncClient(timeout=attesa) as client:
                r = await client.post(
                    self.profilo["indirizzo"].rstrip("/") + "/chat/completions",
                    json=corpo, headers={"Authorization": f"Bearer {self.chiave}"})
        except httpx.TimeoutException as e:
            raise ErroreModello(f"Il modello non ha risposto entro {attesa} secondi.") from e
        except httpx.HTTPError as e:
            raise ErroreModello(f"Non riesco a raggiungere il modello ({type(e).__name__}).") from e
        if r.status_code != 200:
            raise ErroreModello(f"Il modello ha risposto con un errore ({r.status_code}): {r.text[:300]}")
        try:
            msg = r.json()["choices"][0]["message"]
        except (ValueError, KeyError, IndexError) as e:
            raise ErroreModello("Risposta del modello non leggibile.") from e
        pulito = {"role": "assistant", "content": msg.get("content") or ""}
        if msg.get("tool_calls"):
            pulito["tool_calls"] = [
                {"id": c.get("id") or f"chiamata_{i}", "type": "function",
                 "function": {"name": c["function"]["name"], "arguments": c["function"].get("arguments") or "{}"}}
                for i, c in enumerate(msg["tool_calls"])]
        return pulito
