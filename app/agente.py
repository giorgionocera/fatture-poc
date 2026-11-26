"""Domande libere: il modello scrive interrogazioni, il codice le esegue e controlla le cifre."""
import asyncio
import json
import re
import time

from . import cifre, provenienza
from .config import prompt_sistema
from .modello import ErroreModello
from .strumenti import STRUMENTI, Dati, ErroreInterrogazione, in_testo

PASSI_PREDEFINITI = {
    "struttura_dati": "Sto ripassando come sono fatte le fatture",
    "analisi_iniziale": "Riguardo quello che avevo già trovato",
    "mostra_grafico": "Preparo il grafico",
}
TROPPI_PASSI = "Questa domanda mi ha fatto girare a vuoto. Prova a chiederla in un altro modo, magari più precisa."
TROPPI_ERRORI = "Non sono riuscito a leggere i dati per questa domanda. Prova a riformularla."
SOLO_DATI = "Ecco i dati, giudicate voi."
SENZA_DATI = "Non sono riuscito a rispondere con cifre verificate. Prova a riformulare la domanda."


def _passo(cosa_cerco: str) -> str:
    cosa = (cosa_cerco or "").strip().rstrip(".")
    if not cosa:
        return "Sto guardando le fatture"
    if re.match(r"(?i)^(sto|cerco|guardo|controllo|conto|sommo|calcolo)\b", cosa):
        return cosa[0].upper() + cosa[1:]
    return "Sto guardando " + cosa[0].lower() + cosa[1:]


def cifra_principale(testo: str) -> tuple[str | None, str]:
    """La cifra tra asterischi, o il primo importo in euro. Restituisce (cifra, testo senza asterischi)."""
    m = re.search(r"\*\*(.+?)\*\*", testo)
    pulito = re.sub(r"\*\*(.+?)\*\*", r"\1", testo).replace("**", "").strip()
    if m and any(c.isdigit() for c in m.group(1)) and len(m.group(1)) <= 40:
        return m.group(1).strip(), pulito
    m = re.search(r"\d[\d.]*,\d{2}\s?€", pulito)
    return (m.group(0) if m else None), pulito


class Agente:
    def __init__(self, cfg: dict, modello, dati: Dati, registro=None):
        self.cfg = cfg
        self.modello = modello
        self.dati = dati
        self.registro = registro
        self.imp = cfg["modello"]
        self._analisi = None
        self._prompt = None

    def analisi(self) -> dict:
        if self._analisi is None:
            self._analisi = self.dati.analisi(self.cfg.get("analisi"))
        return self._analisi

    def _per_il_modello(self) -> dict:
        """I risultati delle regole senza gli elenchi di fatture, che servono solo alla provenienza."""
        a = self.analisi()
        snella = {k: v for k, v in a.items() if k != "panoramica"}
        for regola in ("doppioni", "aumenti", "prezzi_diversi", "canoni_dopo_fine"):
            snella[regola] = [{k: v for k, v in caso.items() if k not in ("fatture", "serie")} for caso in a[regola]]
        return snella

    def _log(self, evento, **dati):
        if self.registro:
            self.registro.scrivi(evento, **dati)

    async def rispondi(self, domanda: str, storia: list[dict] | None = None, su_passo=None) -> dict:
        """Risponde a una domanda. Restituisce la scheda da mostrare."""
        inizio = time.monotonic()
        avvisa = su_passo or (lambda _t: None)
        if self._prompt is None:
            self._prompt = prompt_sistema(self.cfg, json.dumps(self.dati.struttura(), ensure_ascii=False, indent=1))
        messaggi = [{"role": "system", "content": self._prompt}, *(storia or []), {"role": "user", "content": domanda}]
        risultati, interrogazioni, passi_detti = [], [], []
        grafico, ultima, usata_analisi = None, None, False
        errori_sql, riscritta = 0, False
        self._log("domanda", testo=domanda, modello=self.modello.nome)

        def scheda(esito, testo, **extra):
            cifra, pulito = cifra_principale(testo) if esito == "ok" else (None, testo)
            s = {"domanda": domanda, "esito": esito, "testo": pulito, "cifra": cifra,
                 "grafico": grafico if esito in ("ok", "solo_dati") else None,
                 "come": {"passi": passi_detti, "fatture": None, "da_tutte": False},
                 "interrogazioni": interrogazioni, "secondi": round(time.monotonic() - inizio, 1), **extra}
            if esito in ("ok", "solo_dati"):
                fatture = None
                if ultima:
                    fatture = provenienza.fatture_coinvolte(self.dati, ultima["sql"])
                elif usata_analisi:
                    fatture = provenienza.da_analisi(pulito, self.analisi())
                if fatture is not None:
                    s["come"]["fatture"] = fatture
                    s["come"]["totale"] = round(sum(f["importo"] for f in fatture), 2)
            self._log("risposta", domanda=domanda, esito=esito, testo=pulito, secondi=s["secondi"],
                      fatture=len(s["come"]["fatture"] or []))
            return s

        for _ in range(self.imp.get("passi_massimi", 8)):
            try:
                msg = await self.modello.chiedi(messaggi, STRUMENTI)
            except ErroreModello as e:
                self._log("errore_modello", testo=str(e))
                return scheda("errore", "Il modello non risponde. Riprova tra un momento.", dettaglio=str(e))
            messaggi.append(msg)

            if msg.get("tool_calls"):
                for chiamata in msg["tool_calls"]:
                    nome = chiamata["function"]["name"]
                    try:
                        argomenti = json.loads(chiamata["function"]["arguments"] or "{}")
                    except ValueError:
                        argomenti = {}
                    detto = _passo(argomenti.get("cosa_cerco")) if nome == "interroga" else PASSI_PREDEFINITI.get(nome, "Sto guardando le fatture")
                    if detto not in passi_detti:
                        passi_detti.append(detto)
                    avvisa(detto)
                    try:
                        if nome == "struttura_dati":
                            esito = self.dati.struttura()
                        elif nome == "analisi_iniziale":
                            esito = self._per_il_modello()
                            risultati.append(esito)
                            usata_analisi = True
                        elif nome == "interroga":
                            sql = argomenti.get("sql", "")
                            esito = await asyncio.to_thread(self.dati.interroga, sql, self.imp.get("righe_massime", 200))
                            ultima = {"sql": sql, "risultato": esito}
                            interrogazioni.append(sql)
                            risultati.append(esito)
                        elif nome == "mostra_grafico":
                            sql = argomenti.get("sql", "")
                            dati_grafico = await asyncio.to_thread(self.dati.interroga, sql, 24)
                            punti = [{"etichetta": str(r[0]), "valore": r[1]} for r in dati_grafico["righe"]
                                     if len(r) >= 2 and isinstance(r[1], (int, float))]
                            if not punti:
                                raise ErroreInterrogazione("Il grafico vuole due colonne: etichetta e valore numerico.")
                            grafico = {"tipo": "linea" if argomenti.get("tipo") == "linea" else "barre",
                                       "titolo": argomenti.get("titolo", ""), "punti": punti}
                            interrogazioni.append(sql)
                            risultati.append(dati_grafico)
                            esito = {"esito": "grafico disegnato", "punti": punti}
                        else:
                            esito = {"errore": f"Strumento sconosciuto: {nome}"}
                        self._log("strumento", nome=nome, argomenti=argomenti, risultato=esito)
                    except ErroreInterrogazione as e:
                        errori_sql += 1
                        esito = {"errore": str(e)}
                        self._log("strumento", nome=nome, argomenti=argomenti, errore=str(e))
                    messaggi.append({"role": "tool", "tool_call_id": chiamata["id"], "name": nome, "content": in_testo(esito)})
                if errori_sql >= self.imp.get("tentativi_interrogazione", 3):
                    return scheda("limite", TROPPI_ERRORI)
                continue

            testo = (msg.get("content") or "").strip()
            if not testo:
                messaggi.append({"role": "user", "content": "Rispondi alla domanda in una o due frasi."})
                continue
            sbagliate = cifre.non_verificate(testo, risultati, [domanda, *interrogazioni])
            if not sbagliate:
                return scheda("ok", testo)
            self._log("cifre_non_verificate", testo=testo, cifre=sbagliate)
            if not riscritta:
                riscritta = True
                avvisa("Ricontrollo le cifre")
                messaggi.append({"role": "user", "content":
                    "Queste cifre non compaiono nei risultati delle interrogazioni: " + ", ".join(sbagliate) +
                    ". Riscrivi la risposta usando solo cifre presenti nei risultati; se ti serve un conto, fallo fare a un'interrogazione."})
                continue
            if ultima and ultima["risultato"]["righe"]:
                return scheda("solo_dati", SOLO_DATI, tabella={"colonne": ultima["risultato"]["colonne"],
                                                                "righe": ultima["risultato"]["righe"][:30]})
            return scheda("limite", SENZA_DATI)
        return scheda("limite", TROPPI_PASSI)


def per_la_storia(schede: list[dict], quante: int) -> list[dict]:
    """Gli ultimi scambi, per capire domande come "e di che colore?"."""
    storia = []
    for s in schede[-quante:] if quante else []:
        if s.get("esito") != "ok":
            continue
        storia.append({"role": "user", "content": s["domanda"]})
        storia.append({"role": "assistant", "content": s["testo"]})
    return storia
