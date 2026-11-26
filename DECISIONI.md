# Decisioni

Scelte non coperte dalla specifica, prese con il criterio "la più semplice e la più affidabile dal vivo".

## Struttura e avvio

- **Docker**, su richiesta di chi presenta. L'app gira in un contenitore (Python 3.13); sul portatile serve solo Docker Desktop. La porta è pubblicata su `127.0.0.1:8002`: raggiungibile solo da questo computer, e diversa dalla 8000 della demo 1, così le due possono restare accese insieme.
- **L'immagine va costruita con la rete accesa** (`./demo avvia` la prima volta). Dopo, l'unica connessione è quella al modello.
- **Python, FastAPI, `httpx`, `sqlglot`, SQLite.** Nessuna libreria del fornitore del modello: `app/modello.py` parla il protocollo compatibile OpenAI.
- **Pagina senza framework e senza passaggi di compilazione**: un file HTML, uno CSS, due JavaScript. Caratteri Inter e JetBrains Mono inclusi in `app/static/fonts/` (licenza OFL), gli stessi della famiglia grafica dell'intervento.
- **Grafici disegnati dal codice dell'app** (`app/static/grafici.js`): barre e linea. Niente libreria esterna da includere o aggiornare.
- **`config.toml` ricalca quello della demo 1** (`[impresa]`, `[impresa.tema]`, `[modello]`, `[[profili]]`, chiave in `.env` come `CHIAVE_FRONTIERA`). Ho letto solo il formato; nessun codice è condiviso o copiato.
- **Moduli separati** per collegamento al modello (`modello.py`), configurazione (`config.py`) e stile (`static/stile.css`), come chiede il LEGGIMI.

## Caricamento

- **Il browser legge la cartella trascinata** e manda i file XML al server, che li salva in `lavoro/fatture/` e costruisce `lavoro/fatture.db`. Funziona anche il clic sul riquadro, che apre la scelta della cartella.
- **`fornitori.csv` non sta nella cartella trascinata**: il percorso è in `config.toml` (`[dati] fornitori`) e punta al file in `contesto/dati/`.
- **`app/caricamento.py` riscrive lo script di riferimento** con le stesse convenzioni e lo stesso schema; i test lo confrontano con `contesto/dati/risposte_attese.json`. In più: un file XML illeggibile viene saltato ed elencato, invece di fermare tutto.
- **Tempi a schermo**: ogni casella resta accesa almeno 1,8 secondi (`[pagina] secondi_per_casella`), anche se il caricamento vero dura un decimo di secondo.

## Prima analisi

- **La luce resta fuori dal totale** per configurazione: la regola degli aumenti trova cera, crema massaggio e luce; gli aumenti nelle categorie di `[analisi] categorie_fuori_totale` (oggi "Energia e acqua") si mostrano nella scheda e in "Peseranno ancora", ma non entrano nei 2.733,66 €.
- **"Ho trovato 4 cose da guardare"** conta le voci del totale: fattura doppia, canone dopo il ritiro, aumenti (una voce per fornitore), stesso articolo a due prezzi.
- **Stesso articolo, prezzi diversi**: si confronta l'ultimo prezzo di ogni fornitore; il risparmio è pezzi comprati sopra il prezzo più basso per la differenza.
- **Canoni dopo la fine**: valgono le righe che contengono "canone" dello stesso fornitore, per articoli già fatturati prima del ritiro. Se la riga di ritiro nomina il macchinario, vale solo il suo canone.
- **Le frasi del modello passano dal controllo delle cifre** come le risposte. Una frase con una cifra che non sta nei risultati viene sostituita da quella scritta dal codice. Lo stesso se il modello non risponde entro 20 secondi (`[analisi] attesa_frasi_secondi`): la prima analisi non dipende mai dalla rete.
- **Le scoperte avanzano quando lo decide chi presenta** (freccia destra, spazio o invio a campo vuoto, o clic). La specifica non dice come; a tempo fisso la scheda scorreva via prima che si finisse di leggerla. Con `[pagina] secondi_tra_scoperte` maggiore di zero si torna all'avanzamento automatico.
- **Scheda "Cosa non torna"**: la cifra grande è la somma delle tre voci (2.479,00 €); il totale di 2.733,66 € sta solo a destra, sul verde lime.
- **La fattura doppia viene segnata** nell'elenco di sinistra quando compare la terza scoperta.

## Domande libere

- **`interroga` ha un secondo argomento, `cosa_cerco`**: il modello ci scrive in parole semplici cosa sta guardando. Serve per il messaggio mentre lavora ("Sto guardando le fatture della luce") e per la frase di "Come l'ho calcolato". La specifica prevede solo l'interrogazione.
- **La struttura dei dati sta già nel prompt di sistema** (tabelle, convenzioni, categorie, fornitori, i 51 articoli, i colori degli smalti), così il modello non spende un passo per chiederla. Lo strumento `struttura_dati` resta disponibile.
- **Prompt affinato** rispetto alla specifica (`prompt_sistema.txt`): cifra principale tra asterischi; "quanto mi costa X" = totale e media al mese, senza corsi e voci che lo nominano soltanto; "quanti X" = quantità, spesa e pezzi per confezione; comprato non vuol dire usato. Da riprovare con il modello di frontiera.
- **Cifra in grande**: è quella che il modello scrive tra asterischi; se manca, il primo importo in euro del testo. Passa comunque dal controllo delle cifre.
- **Controllo delle cifre** (`app/cifre.py`). Una cifra è buona se coincide, a meno di arrotondamento e formato, con: un valore dei risultati (anche dentro un testo, come "conf. 100 pz" o una data); il numero di righe di un risultato; un numero scritto nella domanda o nelle interrogazioni di quella domanda (le costanti che il modello ha messo nel filtro, per esempio il 100 di "confezioni × 100"). I numeri in lettere non si controllano. Una frazione vale come percentuale solo se il numero è seguito da "%".
- **Dopo la riscrittura** il modello può fare altre interrogazioni, dentro il limite di 8 passi. Se la cifra non torna ancora: solo la tabella, con "Ecco i dati, giudicate voi". Se non c'è nessuna tabella: invito a riformulare.
- **Provenienza** (`app/provenienza.py`). Dall'ultima interrogazione si prende la SELECT che legge fatture o righe, se ne tengono tabelle e filtro e si chiede alla base dati quali fatture passano. Per le righe l'importo mostrato è la somma delle righe che contano, non il totale della fattura. Se la risposta viene da `analisi_iniziale`, le fatture sono quelle dei casi di cui il testo nomina il fornitore. Un'interrogazione senza filtro (una percentuale sul totale) mostra tutte le fatture: è vero, anche se poco utile.
- **Memoria**: al modello passano gli ultimi 4 scambi riusciti (`domande_ricordate`), per domande come "di che colore ne compro di più?" dopo gli smalti.
- **Sola lettura a tre livelli**: base dati aperta in sola lettura, solo SELECT (o WITH … SELECT), e un controllo di SQLite che rifiuta ogni azione diversa dalla lettura.
- **Grafico**: al massimo 24 punti; i suoi valori contano come risultati per il controllo delle cifre.

## Pagina

- **Colore d'accento corallo** (`#E8452C`), in `config.toml`. Il verde lime compare solo nel riquadro "Trovato finora".
- **Pagina a misura fissa, in scala**: disegnata per 1920×1080, si adatta in proporzione alla finestra, così sul portatile si vede quello che si vedrà sul proiettore.
- **Le tre caselle si rimpiccioliscono** dopo il caricamento e restano in alto, per lasciare spazio alla conversazione.
- **Una scheda alla volta in vista**: la conversazione scorre e porta in vista l'ultima scheda; le precedenti si rivedono scorrendo.
- **Importi formattati a mano**: il formato italiano del browser non mette il punto nei numeri di quattro cifre (2733,66).
- **Stato su file** (`lavoro/stato.json`): se si ricarica la pagina a metà demo si ritrova tutto. Dopo `./demo reset` la pagina aperta si ricarica da sola.
- **Il reset non cancella il registro.**

## Replay

- **Cosa si registra**: le tre frasi del modello e il tempo impiegato (`registrazioni/prima_analisi.json`), a ogni prima analisi riuscita. In replay le regole girano davvero, quindi le cifre sono sempre quelle delle fatture caricate.
- **Attivazione**: Opzione+R; un puntino grigio in alto a destra indica che è attivo.
- **La registrazione inclusa** viene dal modello locale usato nello sviluppo: si sostituisce da sola alla prima analisi riuscita con il modello di frontiera.

## Modelli

- **Profilo di frontiera**: stesso indirizzo e stesso modello del `config.toml` della demo 1, da confermare. La chiave non è nel repository: senza `.env` la pagina funziona fino alla prima analisi (con le frasi del codice) e alle domande risponde con un messaggio chiaro.
- **Profilo locale (`gemma4:26b` su Ollama): solo per lo sviluppo, non per il palco.** Sulla batteria: 8 domande giuste su 25 senza "ragionamento" (2–9 secondi a domanda); con il ragionamento acceso 17–33 secondi a domanda, oltre il limite di 20. Il controllo delle cifre impedisce comunque che una cifra inventata vada a schermo, ma troppe domande restano senza una risposta utile. Si attiva con `PROFILO=locale ./demo avvia`.
- **`parametri` nel profilo**: valori in più passati al modello così come sono (per il locale, `reasoning_effort = "none"`).
- **La batteria con il modello di frontiera non è ancora stata eseguita**: manca la chiave. È il primo test da fare (`./demo prova`).
