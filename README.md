# Demo 2 – Le fatture che parlano

Chi presenta trascina la cartella con le fatture elettroniche ricevute in un anno da un centro estetico (inventato). L'applicazione le legge, mostra tre scoperte con la cifra dei soldi recuperabili e poi risponde alle domande scritte a mano, mostrando sempre da quali fatture viene ogni cifra.

Applicazione a sé: non dipende dalla demo 1 e non ne condivide codice. Specifica e dati di riferimento stanno in `contesto/`.

## Installazione (macOS)

Serve solo [Docker Desktop](https://www.docker.com/products/docker-desktop/), acceso.

```
cp .env.example .env        # poi scrivi nel file la chiave del modello di frontiera
./demo avvia                # la prima volta costruisce l'immagine: serve la rete
```

Si apre `http://localhost:8002`. Metti la finestra a tutto schermo (la pagina è disegnata per 1920×1080 e si adatta in proporzione).

Modello, indirizzo e nome dell'impresa stanno in `config.toml`; la chiave sta in `.env`. Dopo una modifica: `./demo riavvia`.

## Sul palco

1. `./demo reset` prima di cominciare: pagina vuota, nessuna fattura.
2. Trascina sulla pagina la cartella `contesto/dati/fatture` (meglio una copia sul desktop). In alternativa, clic sul riquadro e scegli la cartella.
3. Le tre caselle si accendono, poi compare la prima scoperta. **Per passare alla scoperta successiva: freccia destra** (oppure spazio o invio a campo vuoto, oppure clic su "Prossima scoperta"). La cifra a destra sale a ogni scoperta fino a 2.733,66 €.
4. "Come l'ho calcolato" si apre con un clic e mostra le fatture da cui viene la cifra.
5. Scrivi le domande nel campo in basso e premi invio.
6. Un clic su una fattura dell'elenco, o sul suo numero in "Come l'ho calcolato", la apre in un'altra scheda in forma leggibile.
7. Per controllare una risposta, cerca il fornitore nel campo sopra l'elenco di sinistra: restano le sue fatture, con il numero e la somma senza IVA.

| Tasto | Cosa fa |
| --- | --- |
| Freccia destra | Scoperta successiva |
| Opzione+R | Attiva o spegne il replay della prima analisi (puntino grigio in alto a destra): ripropone l'ultima esecuzione riuscita senza chiamare il modello |

Se il modello non risponde durante la prima analisi, cifre e schede escono comunque: le calcola il codice, e le tre frasi di accompagnamento le scrive il codice al posto del modello.

## Farla vedere su un altro computer

Di norma l'app risponde solo da questo computer. Per aprirla agli altri computer della stessa rete:

```
./demo avvia --rete        # stampa l'indirizzo, per esempio http://192.168.1.20:8002
./demo avvia               # la richiude
```

- **Non c'è nessuna protezione**: chiunque sia su quella rete può aprire la pagina, fare domande (che consumano la chiave del modello) e fare il reset. Va bene su una rete di casa o su un hotspot proprio, non sul Wi-Fi di una sala.
- **La sessione è una sola**: i due computer vedono le stesse fatture e le stesse schede, ma una pagina non si aggiorna quando l'altra fa una domanda: va ricaricata.
- **La cartella si trascina dal computer che ha la pagina aperta**, quindi deve trovarsi su quello. In alternativa si carica da questo Mac e sull'altro si ricarica la pagina.
- Se l'altro computer non raggiunge la pagina, controllare il firewall di macOS (Impostazioni di Sistema, Rete, Firewall) e che i due siano sulla stessa rete.

Se l'altro computer deve solo guardare, è più semplice duplicare lo schermo.

## Comandi

| Comando | Cosa fa |
| --- | --- |
| `./demo avvia` | Costruisce, accende e apre la pagina |
| `./demo avvia --rete` | Come `avvia`, ma raggiungibile anche dagli altri computer della stessa rete; stampa l'indirizzo da aprire |
| `./demo ferma` / `riavvia` | Spegne / riaccende (un riavvio lascia l'app aperta alla rete, se lo era) |
| `./demo reset` | Stato iniziale, senza fatture (la pagina aperta si ricarica da sola) |
| `./demo test` | Test automatici: caricamento, quattro regole, sola lettura, controllo delle cifre, agente |
| `./demo verifica` | Numeri del caricamento e totale recuperabile |
| `./demo prova [numeri]` | Lancia le 25 domande di prova e scrive `lavoro/resoconto_prova.md` |
| `./demo riformulazioni` | Le 25 domande chieste in altri due modi; resoconto in `lavoro/resoconto_riformulazioni.md` |
| `./demo fuori` | Dieci domande su cose che nelle fatture non ci sono; resoconto in `lavoro/resoconto_fuori_dai_dati.md` |
| `./demo domanda "..."` | Una domanda da riga di comando, con interrogazioni e fatture |
| `./demo video ["domanda"]` | Registra un video della demo in `video/demo_fatture.mp4` (circa 70 secondi): caricamento, tre scoperte, una domanda (predefinita: il caffè) con "Come l'ho calcolato". Usa l'app accesa e il modello vero; alla fine riporta l'app allo stato iniziale |
| `./demo registro [n]` | Ultime righe del registro (`lavoro/registro.jsonl`) |
| `./demo diario` | Messaggi del server |

## Test di accettazione (specifica, sezione 9)

| Test | Come si verifica | Stato |
| --- | --- | --- |
| Caricamento | `./demo test` (`tests/test_caricamento.py`) | automatico |
| Prima analisi, 10 su 10 | `./demo test` (`tests/test_regole.py`) | automatico |
| Controllo delle cifre | `./demo test` (`tests/test_cifre.py`, `tests/test_agente.py`: un numero inventato non arriva a schermo) | automatico |
| Sola lettura | `./demo test` (`tests/test_strumenti.py`) | automatico |
| Reset | `./demo reset` | comando |
| Domande di prova, almeno 23 su 25 | `./demo prova`, poi leggere `lavoro/resoconto_prova.md` | 25 su 25 con Sonnet 5.5 (26/11/2026); da ripetere sul portatile del palco |
| Riformulazioni | `./demo riformulazioni` (50 domande in `prove/riformulazioni.json`) | 49 su 50, la cinquantesima è giusta per come è scritta la domanda |
| Fuori dai dati, 10 su 10 | `./demo fuori` (10 domande in `prove/fuori_dai_dati.json`) | 10 su 10 |
| Tempi | Colonna "Secondi" del resoconto; `secondi` in `lavoro/registro.jsonl` per la prima analisi | da eseguire sul portatile del palco |
| Indipendenza | Clonare il repository su un portatile senza la demo 1 e fare `./demo avvia` | da eseguire |
| Proiettore | Guardare dall'ultima fila cifre, grafici e "Come l'ho calcolato" | da eseguire in sala |

Il video di riserva lo registra chi presenta, con tre domande libere. `./demo video` ne fa uno automatico, utile come anteprima o per mandarlo a chi organizza, ma non lo sostituisce: gira senza interfaccia, con il cursore disegnato e la cartella scelta dal riquadro invece che trascinata.

## Com'è fatta

```
app/
  config.py        configurazione (config.toml, profili di modello)
  modello.py       collegamento al modello: l'unica chiamata di rete
  caricamento.py   XML FatturaPA -> SQLite (tabelle fatture e righe, viste *_valide)
  regole.py        le quattro regole della prima analisi
  analisi.py       le tre schede; il modello scrive solo le frasi; replay
  strumenti.py     i quattro strumenti dell'agente, base dati in sola lettura
  agente.py        ciclo delle domande libere
  cifre.py         controllo delle cifre
  provenienza.py   dalle interrogazioni alle fatture coinvolte
  registro.py      registro di domande, interrogazioni e risultati
  server.py        le pagine e le API
  cli.py           batteria di prova e comandi da terminale
  static/          pagina, lettore della fattura, stile, grafici, caratteri (tutto locale)
tests/             test automatici
prove/             riformulazioni e domande fuori dai dati
contesto/          specifica, fatture e numeri attesi (non si modifica)
lavoro/            fatture caricate, base dati, stato, registro, resoconti (non versionata)
registrazioni/     l'ultima prima analisi riuscita, per il replay
```

Le scelte non coperte dalla specifica sono in `DECISIONI.md`.
