"""Prima analisi: le regole fanno i conti, il codice compone le tre schede, il modello scrive solo le frasi.

Se il modello non risponde, o scrive una cifra che non sta nei risultati, vale la frase scritta dal codice.
Ogni esecuzione riuscita viene registrata: il replay la ripropone con gli stessi tempi, senza chiamare il modello.
"""
import asyncio
import json
import re
import time
from datetime import datetime

from . import cifre
from .config import REGISTRAZIONI
from .formato import del_giorno, euro, il_giorno, intero, mese, nome_breve, percento, prezzo
from .modello import ErroreModello

FILE_REPLAY = REGISTRAZIONI / "prima_analisi.json"

ISTRUZIONI = """Sei l'assistente di {nome}. Hai appena guardato tutte insieme le fatture ricevute in un anno.
Qui sotto ci sono i risultati dei controlli, già calcolati. Scrivi tre frasi di accompagnamento, una per scheda,
per un pubblico di artigiani: italiano semplice, tono diretto, al massimo 22 parole ciascuna.
Le cifre grandi sono già a schermo: non ripeterle tutte. Puoi usare solo cifre che compaiono nei risultati.
Niente consigli fiscali o legali, niente termini tecnici. Scrivi i nomi dei fornitori senza S.r.l. o S.p.A.

Rispondi solo con un oggetto JSON con tre chiavi:
"soldi": dove vanno i soldi (le voci di spesa più grandi);
"prezzi": chi ha alzato i prezzi e come;
"non_torna": cosa non torna (fattura doppia, canone dopo il ritiro, stesso articolo a due prezzi).

Risultati:
{risultati}"""


def frasi_del_codice(a: dict) -> dict:
    cat = a["panoramica"]["categorie"]
    frasi = {"soldi": "", "prezzi": "Nessun prezzo è salito in modo rilevante.", "non_torna": "Non ho trovato nulla che non torni."}
    if len(cat) >= 2:
        frasi["soldi"] = (f"La voce più grande è {cat[0]['categoria'].lower()}, poi {cat[1]['categoria'].lower()}: "
                          f"insieme fanno quasi metà della spesa." if cat[0]["quota_percento"] + cat[1]["quota_percento"] >= 40
                          else f"La voce più grande è {cat[0]['categoria'].lower()}, poi {cat[1]['categoria'].lower()}.")
    nel_totale = [x for x in a["aumenti"] if x["nel_totale"]]
    if nel_totale:
        frasi["prezzi"] = (f"{nome_breve(nel_totale[0]['fornitore'])} ha ritoccato i prezzi un poco alla volta: "
                           f"mese per mese non si nota, in un anno sì.")
    elif a["aumenti"]:
        frasi["prezzi"] = "Un prezzo è salito durante l'anno."
    trovate = []
    if a["doppioni"]:
        trovate.append("una fattura arrivata due volte")
    if a["canoni_dopo_fine"]:
        trovate.append("un canone pagato dopo il ritiro del macchinario")
    if a["prezzi_diversi"]:
        trovate.append("lo stesso articolo comprato a due prezzi")
    if trovate:
        elenco = ", ".join(trovate[:-1]) + (" e " if len(trovate) > 1 else "") + trovate[-1]
        frasi["non_torna"] = elenco[0].upper() + elenco[1:] + "."
    return frasi


def _snella(a: dict) -> dict:
    s = {"panoramica": {k: v for k, v in a["panoramica"].items() if k != "mesi"}}
    s["panoramica"]["categorie"] = a["panoramica"]["categorie"][:4]
    for regola in ("doppioni", "aumenti", "prezzi_diversi", "canoni_dopo_fine"):
        s[regola] = [{k: v for k, v in caso.items() if k not in ("fatture", "serie")} for caso in a[regola]]
    s["recuperabile_totale"] = a["recuperabile_totale"]
    return s


async def racconta(modello, cfg: dict, a: dict, registro=None) -> tuple[dict, bool]:
    """Le tre frasi. Restituisce (frasi, tutte_del_modello)."""
    frasi = frasi_del_codice(a)
    snella = _snella(a)
    testo = ISTRUZIONI.replace("{nome}", cfg["impresa"]["nome"]).replace("{risultati}", json.dumps(snella, ensure_ascii=False))
    try:
        attesa = cfg.get("analisi", {}).get("attesa_frasi_secondi", 20)
        msg = await asyncio.wait_for(modello.chiedi([{"role": "user", "content": testo}]), timeout=attesa)
        m = re.search(r"\{.*\}", msg["content"], re.S)
        scritte = json.loads(m.group(0)) if m else {}
    except (ErroreModello, ValueError, asyncio.TimeoutError) as e:
        if registro:
            registro.scrivi("prima_analisi_senza_modello", motivo=str(e) or "il modello non ha risposto in tempo")
        return frasi, False
    buone = 0
    for chiave in frasi:
        frase = scritte.get(chiave)
        if isinstance(frase, str) and 10 < len(frase) < 260 and not cifre.non_verificate(frase, [snella]):
            frasi[chiave] = frase.strip().replace("**", "")
            buone += 1
        elif registro:
            registro.scrivi("frase_scartata", scheda=chiave, frase=frase)
    return frasi, buone == len(frasi)


def componi(a: dict, frasi: dict) -> dict:
    """Le tre schede e il riquadro "trovato finora". Tutte le cifre vengono dalle regole."""
    p = a["panoramica"]
    voci = a["voci_recuperabili"]
    di = lambda regola: [v for v in voci if v["regola"] == regola]
    tutte = lambda regola: [f for caso in a[regola] for f in caso["fatture"]]

    soldi = {
        "id": "soldi", "numero": "01", "titolo": "Dove vanno i soldi", "frase": frasi["soldi"],
        "cifra": euro(p["spesa_totale"]), "sotto_cifra": f"spesi in un anno, IVA esclusa · {euro(p['media_mensile'])} al mese",
        "grafico": {"tipo": "barre", "titolo": "Le voci di spesa più grandi", "unita": "€",
                    "punti": [{"etichetta": c["categoria"], "valore": c["spesa"], "nota": percento(c["quota_percento"])}
                              for c in p["categorie"][:5]]},
        "voci": [], "aggiunge": [],
        "come": {"testo": f"Ho sommato gli importi senza IVA di tutte le {p['fatture']} fatture, voce per voce. "
                          f"La fattura arrivata due volte è contata una volta sola.", "fatture": None},
    }

    voci_prezzi = []
    for x in a["aumenti"]:
        nota = (f"{nome_breve(x['fornitore'])}: da {prezzo(x['prezzo_iniziale'])} a {prezzo(x['prezzo_finale'])}"
                + (f" in {x['numero_ritocchi']} ritocchi" if x["numero_ritocchi"] > 1 else f" da {mese(x['primo_mese_aumento'])}"))
        if not x["nel_totale"]:
            nota += f" · {euro(x['maggior_costo'])} in più finora, fuori dal totale"
        voci_prezzi.append({"nome": x["articolo"], "valore": "+" + percento(x["aumento_percento"]), "nota": nota})
    pagato = round(sum(v["importo"] for v in di("aumenti")), 2)
    prezzi = {
        "id": "prezzi", "numero": "02", "titolo": "Chi ha alzato i prezzi", "frase": frasi["prezzi"],
        "cifra": euro(pagato), "sotto_cifra": "già pagati in più rispetto ai prezzi di partenza",
        "grafico": None, "voci": voci_prezzi, "aggiunge": di("aumenti"),
        "come": {"testo": "Per ogni articolo ho confrontato il primo prezzo dell'anno con quelli pagati dopo: "
                          "quantità comprata per la differenza di prezzo, riga per riga.",
                 "fatture": [f for x in a["aumenti"] if x["nel_totale"] for f in x["fatture"]]},
    }

    voci_torna = []
    for c in a["doppioni"]:
        voci_torna.append({"nome": "Fattura doppia", "valore": euro(c["imponibile"]),
                           "nota": f"{nome_breve(c['fornitore'])}, fattura {c['numero']} {del_giorno(c['data'])}: è arrivata in due file identici"})
    for c in a["canoni_dopo_fine"]:
        voci_torna.append({"nome": "Canone dopo il ritiro", "valore": euro(c["importo_non_dovuto"]),
                           "nota": f"{nome_breve(c['fornitore'])}: macchinario ritirato {il_giorno(c['data_fine'])}, "
                                   f"poi altri {c['canoni_dopo_la_fine']} canoni da {euro(c['canone'])}"})
    for c in a["prezzi_diversi"]:
        voci_torna.append({"nome": "Stesso articolo, due prezzi", "valore": euro(c["risparmio_possibile"]),
                           "nota": f"{c['articolo']}: {prezzo(c['prezzo_basso'])} da {nome_breve(c['fornitore_conveniente'])}, "
                                   f"{prezzo(c['prezzo_alto'])} da {nome_breve(c['fornitore_caro'])} "
                                   f"({intero(c['pezzi_al_prezzo_alto'])} pezzi al prezzo alto)"})
    aggiunge = di("doppioni") + di("canoni_dopo_fine") + di("prezzi_diversi")
    non_torna = {
        "id": "non_torna", "numero": "03", "titolo": "Cosa non torna", "frase": frasi["non_torna"],
        "cifra": euro(round(sum(v["importo"] for v in aggiunge), 2)), "sotto_cifra": "da recuperare o risparmiare",
        "grafico": None, "voci": voci_torna, "aggiunge": aggiunge,
        "come": {"testo": "Ho cercato file con stesso fornitore, numero, data e totale; canoni fatturati dopo una riga "
                          "di ritiro; lo stesso articolo comprato da fornitori diversi a prezzi diversi.",
                 "fatture": tutte("doppioni") + tutte("canoni_dopo_fine") + tutte("prezzi_diversi")},
    }
    return {
        "scoperte": [soldi, prezzi, non_torna],
        "cose_trovate": a["cose_trovate"],
        "trovato": {"totale": a["recuperabile_totale"], "voci": [], "futuro": a["aumenti_che_pesano_sul_futuro"]},
        "doppioni": [c["file_doppio"] for c in a["doppioni"]],
    }


async def esegui(modello, cfg: dict, a: dict, replay: bool = False, registro=None) -> dict:
    """Prima analisi completa. In replay non chiama il modello e rispetta i tempi registrati."""
    inizio = time.monotonic()
    usato_replay = False
    if replay and FILE_REPLAY.exists():
        registrata = json.loads(FILE_REPLAY.read_text(encoding="utf-8"))
        frasi = {**frasi_del_codice(a), **registrata["frasi"]}
        await asyncio.sleep(max(0.0, min(registrata.get("secondi", 3), 30) - (time.monotonic() - inizio)))
        usato_replay = True
    else:
        frasi, tutte = await racconta(modello, cfg, a, registro)
        if tutte:
            REGISTRAZIONI.mkdir(parents=True, exist_ok=True)
            FILE_REPLAY.write_text(json.dumps({
                "frasi": frasi, "secondi": round(time.monotonic() - inizio, 1), "modello": modello.nome,
                "registrata_il": datetime.now().isoformat(timespec="seconds")}, ensure_ascii=False, indent=2), encoding="utf-8")
    esito = componi(a, frasi)
    esito["replay"] = usato_replay
    esito["secondi"] = round(time.monotonic() - inizio, 1)
    if registro:
        registro.scrivi("prima_analisi", replay=usato_replay, secondi=esito["secondi"], frasi=frasi,
                        recuperabile=a["recuperabile_totale"], voci=a["voci_recuperabili"])
    return esito
