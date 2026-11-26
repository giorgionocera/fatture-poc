"""La pagina "Come funziona": lo schema dell'applicazione, con i valori letti dal vivo.

Ogni parte dello schema ha un titolo, una riga breve (sotto il titolo nel riquadro) e un dettaglio per il pannello:
testo, voci chiave-valore, elenchi e, chiusi, i dettagli tecnici. Nessun valore è scritto a mano: modello,
limiti e soglie vengono da config.toml, i numeri dalla base dati e dal registro.
La chiave del modello non compare mai: si dice solo se c'è.
"""
import json
import sqlite3
from pathlib import Path

from .config import LAVORO, REGISTRAZIONI, chiave_del_profilo, file_fornitori, profilo_attivo, prompt_sistema
from .formato import data, euro, intero, mese, percento
from .strumenti import COLONNE, CONVENZIONI, STRUMENTI

# Gli strumenti spiegati a chi guarda: titolo, cosa fa, cosa gli scrive il modello (None se niente), cosa torna al modello.
# La descrizione per il modello resta nei dettagli tecnici.
SPIEGAZIONI = {
    "struttura_dati": ("La struttura",
        "Restituisce tabelle e colonne, le regole di lettura, le voci di spesa, i fornitori, gli articoli e il periodo "
        "coperto. Serve al modello per sapere dove cercare prima di scrivere una ricerca. La stessa descrizione è già "
        "nelle sue istruzioni, quindi lo usa di rado.", None,
        "tabelle, voci, fornitori, articoli"),
    "analisi_iniziale": ("Le scoperte",
        "Restituisce quello che hanno trovato le quattro regole, con le loro cifre: fattura doppia, aumenti, stesso "
        "articolo a prezzi diversi, canoni dopo il ritiro. Il modello lo usa quando la domanda riguarda queste cose, "
        "così risponde con gli stessi numeri delle schede.", None,
        "le quattro cose trovate e le cifre"),
    "interroga": ("La ricerca",
        "Il modello scrive una ricerca nella base dati e dice in parole semplici cosa sta guardando: è la frase che "
        "compare nella scheda mentre lavora. Il codice la esegue senza poter modificare nulla e gli restituisce le righe "
        "trovate. Somme, medie e percentuali le fa fare qui, così le cifre passano il controllo.",
        "la ricerca e cosa sta guardando",
        "le righe trovate (al massimo {righe})"),
    "mostra_grafico": ("Il grafico",
        "Il modello sceglie barre, linea o torta, un titolo e una ricerca che restituisce etichetta e valore. Il codice "
        "esegue la ricerca e disegna il grafico nella scheda: linea per gli andamenti nel tempo, barre per i confronti, "
        "torta per come si divide un totale, con al massimo sei fette (le altre vanno in «Altre»).", "tipo, titolo e dati",
        "nulla: il grafico va a schermo"),
}


def nome_modello(identificativo: str) -> str:
    """'anthropic:claude@sonnet-5.5' -> 'Claude Sonnet 5.5'; gli altri restano come sono."""
    if "claude@" in identificativo:
        famiglia, _, versione = identificativo.split("claude@", 1)[1].partition("-")
        return f"Claude {famiglia.capitalize()} {versione}".strip()
    return identificativo


def _registro() -> dict:
    conta = {"domande": 0, "risposte": 0, "giuste": 0, "solo_dati": 0, "senza": 0, "errori": 0,
             "cifre_fermate": 0, "interrogazioni": 0, "prime_analisi": 0, "ultimo": None, "usi": {}}
    percorso = LAVORO / "registro.jsonl"
    if not percorso.exists():
        return conta
    for riga in percorso.read_text(encoding="utf-8").splitlines():
        try:
            e = json.loads(riga)
        except ValueError:
            continue
        conta["ultimo"] = e.get("quando")
        evento = e.get("evento")
        if evento == "domanda":
            conta["domande"] += 1
        elif evento == "risposta":
            conta["risposte"] += 1
            chiave = {"ok": "giuste", "solo_dati": "solo_dati", "limite": "senza"}.get(e.get("esito"), "errori")
            conta[chiave] += 1
        elif evento == "cifre_non_verificate":
            conta["cifre_fermate"] += 1
        elif evento == "strumento":
            conta["usi"][e.get("nome")] = conta["usi"].get(e.get("nome"), 0) + 1
            if e.get("nome") == "interroga":
                conta["interrogazioni"] += 1
        elif evento == "prima_analisi":
            conta["prime_analisi"] += 1
    return conta


def _secondi(x) -> str:
    return f"{x:.1f}".replace(".", ",") + " s"


def descrivi(cfg: dict, stato: dict, file_db: Path, analisi: dict | None) -> dict:
    imp, mod, regole_cfg = cfg["impresa"], cfg["modello"], cfg.get("analisi", {})
    stat = stato.get("statistiche") if stato.get("caricato") else None
    profilo = profilo_attivo(cfg)
    altri = [p for p in cfg.get("profili", []) if p["id"] != profilo["id"]]
    reg = _registro()
    with open(file_fornitori(cfg), encoding="utf-8") as f:
        fornitori_anagrafica = max(0, sum(1 for _ in f) - 1)

    parti = {}

    # ── Prima analisi ──
    parti["fatture"] = {
        "titolo": "Le fatture", "corsia": "analisi",
        "riga": f"{stat['file']} file" if stat else "nessun file",
        "testo": "La cartella che chi presenta trascina sulla pagina: le fatture elettroniche ricevute in un anno, "
                 "un file per fattura, nel formato che arriva dallo SdI. Impresa, fornitori e prezzi sono inventati.",
        "voci": [["Formato", "FatturaPA (FPR12), un file XML per fattura"]]
                + ([["File letti", intero(stat["file"])], ["Periodo", f"{mese(stat['periodo'][0])} – {mese(stat['periodo'][1])}"],
                    ["Fornitori", intero(stat["fornitori"])], ["Scartati", intero(len(stat.get("scartati", [])))]] if stat else [])
                + [["Anagrafica fornitori", f"{fornitori_anagrafica} fornitori con categoria e regione"]],
        "tecnici": [{"titolo": "Da dove", "testo": "Dati di prova: contesto/dati/fatture\n"
                                                   f"Anagrafica: {cfg.get('dati', {}).get('fornitori')}"}],
    }
    parti["lettura"] = {
        "titolo": "La lettura", "corsia": "analisi",
        "riga": "senza modello",
        "testo": "Il codice legge ogni file e mette fatture e righe in due tabelle. Qui non c'è nessun modello: "
                 "sono regole scritte, sempre uguali.",
        "elenchi": [{"titolo": "Le regole di lettura", "righe": [
            "Spesa = importo senza IVA, salvo quando si chiede il totale con IVA",
            "Le note di credito valgono col segno meno",
            "Una fattura con stesso fornitore, numero, data e totale di una già letta è segnata come doppia e non si conta",
            "Categoria e regione vengono dall'anagrafica dei fornitori",
            "Per gli smalti il colore è tenuto a parte"]}],
    }
    if file_db.exists():
        con = sqlite3.connect(f"file:{file_db}?mode=ro", uri=True)
        conta = lambda t: con.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0]
        numeri = {t: conta(t) for t in ("fatture", "fatture_valide", "righe", "righe_valide")}
        categorie = con.execute("SELECT COUNT(DISTINCT categoria) FROM fatture_valide").fetchone()[0]
        con.close()
        riga_db = f"{intero(numeri['fatture_valide'])} fatture"
        voci_db = [["Fatture", f"{intero(numeri['fatture_valide'])} valide su {intero(numeri['fatture'])}"],
                   ["Righe", f"{intero(numeri['righe_valide'])} valide su {intero(numeri['righe'])}"],
                   ["Voci di spesa", intero(categorie)]]
    else:
        riga_db, voci_db = "vuota", []
    parti["basedati"] = {
        "titolo": "La base dati", "corsia": "analisi", "riga": riga_db,
        "testo": "Un archivio sul portatile, rifatto da capo a ogni caricamento. È l'unica cosa che l'agente può "
                 "leggere, e la legge senza poterla modificare.",
        "voci": voci_db + [["Dove", "sul portatile, mai in rete"], ["Accesso dell'agente", "solo lettura"]],
        "elenchi": [{"titolo": "Le convenzioni che l'agente riceve", "righe": CONVENZIONI}],
        "tecnici": [{"titolo": "Tabelle e colonne", "testo": "\n\n".join(f"{t}:\n{c}" for t, c in COLONNE.items())},
                    {"titolo": "File", "testo": "SQLite: lavoro/fatture.db"}],
    }

    soglia_a = regole_cfg.get("soglia_aumento_percento", 5)
    soglia_p = regole_cfg.get("soglia_differenza_percento", 5)
    righe_regole = [
        f"Doppioni: stesso fornitore, numero, data e totale",
        f"Aumenti: stesso articolo e fornitore, prezzo finale più alto di almeno il {intero(soglia_a)}%",
        f"Stesso articolo, prezzi diversi: fornitori che differiscono di almeno il {intero(soglia_p)}%",
        "Canoni dopo la fine: una riga con " + ", ".join(f"«{p}»" for p in regole_cfg.get("parole_fine_contratto", []))
        + ", poi canoni dello stesso fornitore"]
    voci_regole, riga_regole = [], "4 regole fisse"
    if analisi:
        riga_regole = f"{analisi['cose_trovate']} cose trovate"
        for v in analisi["voci_recuperabili"]:
            voci_regole.append([v["titolo"], euro(v["importo"])])
        voci_regole.append(["Totale", euro(analisi["recuperabile_totale"])])
        fuori = [a for a in analisi["aumenti"] if not a["nel_totale"]]
        for a in fuori:
            voci_regole.append([f"Fuori dal totale: {a['articolo'].split(' – ')[0].lower()}",
                                f"+{percento(a['aumento_percento'])}, {euro(a['maggior_costo'])} finora"])
    parti["regole"] = {
        "titolo": "Le regole", "corsia": "analisi", "riga": riga_regole,
        "testo": "Le cifre delle scoperte le calcola il codice con quattro regole fisse: stesse fatture, stesso risultato, "
                 "ogni volta. Il modello non tocca questi numeri.",
        "elenchi": [{"titolo": "Cosa cercano", "righe": righe_regole}],
        "voci": voci_regole,
        "tecnici": [{"titolo": "Fuori dal totale", "testo": "Aumenti nelle categorie: "
                     + ", ".join(regole_cfg.get("categorie_fuori_totale", [])) + "\n(si mostrano ma non entrano nella cifra trovata)"}],
    }
    replay = None
    if (REGISTRAZIONI / "prima_analisi.json").exists():
        replay = json.loads((REGISTRAZIONI / "prima_analisi.json").read_text(encoding="utf-8"))
    a_schermo = stato.get("analisi")
    parti["scoperte"] = {
        "titolo": "Le scoperte", "corsia": "analisi",
        "riga": (euro(a_schermo['trovato']['totale']) if a_schermo else "non ancora"),
        "testo": "Tre schede: dove vanno i soldi, chi ha alzato i prezzi, cosa non torna. Cifre e tabelle le mette il "
                 "codice; il modello scrive solo una frase di accompagnamento per scheda, che passa dallo stesso "
                 "controllo delle cifre delle risposte. Se il modello non risponde, la frase la scrive il codice.",
        "voci": ([["Ultima esecuzione", ("replay, senza modello" if a_schermo.get("replay") else "con il modello")
                   + f", {_secondi(a_schermo['secondi'])}"]] if a_schermo else [])
                + [["Attesa massima per le frasi", f"{intero(regole_cfg.get('attesa_frasi_secondi', 20))} s"]]
                + ([["Replay (Opzione+R)", f"registrato con {nome_modello(replay.get('modello', ''))}"
                     + (f", {data(replay['registrata_il'][:10])}" if replay.get('registrata_il') else "")]] if replay else
                   [["Replay (Opzione+R)", "nessuna esecuzione registrata"]]),
    }

    # ── Domande libere ──
    parti["domanda"] = {
        "titolo": "La domanda", "corsia": "domande", "riga": "scritta a mano",
        "testo": "Chi presenta scrive la domanda così come arriva dalla sala. L'agente ricorda gli ultimi scambi, "
                 "così capisce domande come «e di che colore ne compro di più?».",
        "voci": [["Scambi ricordati", intero(mod.get("domande_ricordate", 4))], ["Lunghezza massima", "500 caratteri"],
                 ["Domande fatte finora", intero(reg["domande"])]],
    }
    parti["modello"] = {
        "titolo": "Il modello", "corsia": "domande",
        "riga": nome_modello(profilo["modello"]),
        "testo": "Il modello capisce la domanda, decide cosa cercare e scrive la risposta in italiano semplice. "
                 "Non vede le fatture direttamente: le guarda solo attraverso i quattro strumenti, e ogni cifra che scrive "
                 "viene ricontrollata dal codice.",
        "voci": [["In uso", nome_modello(profilo["modello"])],
                 ["Dove gira", "in rete" if profilo.get("dove") == "cloud" else "su questo computer"],
                 ["Chiave", "presente" if chiave_del_profilo(profilo) else "manca: le domande non funzionano"],
                 ["Passi per domanda", f"al massimo {intero(mod.get('passi_massimi', 8))}"],
                 ["Attesa per ogni risposta", f"al massimo {intero(mod.get('attesa_massima_secondi', 60))} s"],
                 ["Temperatura", "zero" if profilo.get("invia_temperatura", True) else "quella predefinita del modello"]],
        "elenchi": [{"titolo": "Altri modelli pronti", "righe": [
            f"{nome_modello(p['modello'])}, {'in rete' if p.get('dove') == 'cloud' else 'su questo computer'}"
            for p in altri]}] if altri else [],
        "tecnici": [{"titolo": "Collegamento", "testo": f"Profilo: {profilo['id']}\nModello: {profilo['modello']}\n"
                                                        f"Indirizzo: {profilo['indirizzo']}\nProtocollo: compatibile OpenAI, con strumenti\n\n"
                                                        + "\n".join(f"Per usare {nome_modello(p['modello'])}: PROFILO={p['id']} ./demo avvia" for p in altri)},
                    {"titolo": "Le sue istruzioni",
                     "testo": prompt_sistema(cfg, "(tabelle, convenzioni, categorie, fornitori e articoli: aggiunti al caricamento)")}],
    }
    parti["strumenti"] = {
        "titolo": "Gli strumenti", "corsia": "domande",
        "riga": f"{intero(sum(reg['usi'].values()))} usi finora",
        "testo": "Gli unici modi in cui il modello può guardare i dati. Il modello scrive la ricerca, il codice la "
                 "esegue sulla base dati e gli restituisce il risultato: è da lì che vengono le cifre.",
        "voci": [["Righe per risultato", f"al massimo {intero(mod.get('righe_massime', 200))}"],
                 ["Tempo per ricerca", f"al massimo {intero(mod.get('secondi_interrogazione', 5))} s"],
                 ["Ricerche sbagliate ammesse", intero(mod.get("tentativi_interrogazione", 3))],
                 ["Ricerche fatte finora", intero(reg["interrogazioni"])]],
        "elenchi": [{"titolo": "Gli strumenti", "righe": [
            f"{SPIEGAZIONI[s['function']['name']][0]} ({s['function']['name']})" for s in STRUMENTI]}],
        "tecnici": [{"titolo": "Come il modello li vede", "testo": json.dumps(STRUMENTI, ensure_ascii=False, indent=1)}],
    }
    for s_ in STRUMENTI:
        nome = s_["function"]["name"]
        titolo, testo, scrive, torna = SPIEGAZIONI[nome]
        voci = [["Nome per il modello", nome]]
        if scrive:
            voci.append(["Il modello gli scrive", scrive])
        voci += [["Torna al modello", torna.format(righe=intero(mod.get("righe_massime", 200)))],
                 ["Usato finora", intero(reg["usi"].get(nome, 0))]]
        if nome == "interroga":
            voci += [["Tempo per ricerca", f"al massimo {intero(mod.get('secondi_interrogazione', 5))} s"],
                     ["Se prova a modificare", "rifiutata"]]
        if nome == "mostra_grafico":
            voci += [["Punti del grafico", "al massimo 24"]]
        parti[f"t_{nome}"] = {"titolo": titolo, "corsia": "domande", "riga": nome, "testo": testo, "voci": voci,
                              "tecnici": [{"titolo": "Come lo vede il modello", "testo": json.dumps(s_, ensure_ascii=False, indent=1)}]}
    parti["controllo"] = {
        "titolo": "Il controllo", "corsia": "domande",
        "riga": (f"{intero(reg['cifre_fermate'])} cifre fermate" if reg["risposte"] else "ogni numero"),
        "testo": "Prima di mostrare una risposta, il codice cerca ogni numero del testo nei risultati delle ricerche di "
                 "quella domanda. Se una cifra non c'è, il modello riscrive una volta; se ancora non torna, a schermo va "
                 "solo la tabella dei dati, con «ecco i dati, giudicate voi». Meglio «non lo so» che una cifra inventata.",
        "voci": [["Risposte date", intero(reg["risposte"])], ["Con cifre verificate", intero(reg["giuste"])],
                 ["Fermate: solo la tabella", intero(reg["solo_dati"])], ["Senza risposta", intero(reg["senza"] + reg["errori"])],
                 ["Riscritture chieste", intero(reg["cifre_fermate"])]],
    }
    parti["risposta"] = {
        "titolo": "La risposta", "corsia": "domande", "riga": "con le fatture",
        "testo": "Ogni scheda ha la cifra in grande, una o due frasi e, richiudibile, «Come l'ho calcolato»: cosa ha "
                 "cercato e le fatture da cui viene la cifra, con fornitore, numero, data e importo. Le fatture si aprono "
                 "con un clic. Il grafico compare solo per andamenti o confronti tra più di tre voci.",
        "elenchi": [{"titolo": "Da dove vengono le fatture elencate", "righe": [
            "Dalla ricerca che contiene la cifra principale della risposta",
            "Se la risposta viene dalla prima analisi, dai casi di cui parla",
            "La ricerca scritta dal modello si vede in «Dettagli tecnici», chiusi di norma"]}],
    }

    for chiave, parte in parti.items():
        parte["id"] = chiave
        for campo in ("voci", "elenchi", "tecnici"):
            parte.setdefault(campo, [])
    return {"impresa": {k: imp.get(k) for k in ("nome", "sigla", "attivita", "tema")}, "parti": parti,
            "in_uso": nome_modello(profilo["modello"])}
