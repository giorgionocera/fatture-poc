# Decisioni

Scelte non coperte dalla specifica, prese con il criterio "la più semplice e la più affidabile dal vivo".

## Struttura e avvio

- **Docker**, su richiesta di chi presenta. L'app gira in un contenitore (Python 3.13); sul portatile serve solo Docker Desktop. La porta è pubblicata su `127.0.0.1:8002`: raggiungibile solo da questo computer, e diversa dalla 8000 della demo 1, così le due possono restare accese insieme.
- **Apertura alla rete locale, spenta di norma** (chiesta da chi presenta): `./demo avvia --rete` pubblica la porta su tutte le interfacce (`ASCOLTO=0.0.0.0` in `compose.yaml`) e stampa l'indirizzo del Mac. `./demo avvia` la richiude; `./demo riavvia` conserva lo stato in cui era. Non c'è autenticazione: è pensata per una rete propria, non per quella della sala.
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
- **"Come l'ho calcolato" delle scoperte 02 e 03 si ricontrolla a mano**: una riga per articolo e fattura, con pezzi, prezzo e quanto entra nella cifra ("Pagato in più", "Da recuperare"), e il totale in fondo, uguale alla cifra della scheda. Ci sono anche le righe che valgono zero (il primo prezzo dell'anno, la fattura originale, il ritiro del macchinario, il gel al prezzo più basso): senza, non si vedeva da dove partiva il confronto. Nella prima versione la tabella elencava solo le fatture dopo il primo ritocco, con la spesa della riga invece di quanto pagato in più, e chi presenta non trovava il 9,80 € di partenza della cera.
- **La nota di ogni aumento dice anche quando**: "da 9,80 € a novembre 2025 a 11,27 € a ottobre 2026, in 7 ritocchi".

## Domande libere

- **`interroga` ha un secondo argomento, `cosa_cerco`**: il modello ci scrive in parole semplici cosa sta guardando. Serve per il messaggio mentre lavora ("Sto guardando le fatture della luce") e per la frase di "Come l'ho calcolato". La specifica prevede solo l'interrogazione.
- **La struttura dei dati sta già nel prompt di sistema** (tabelle, convenzioni, categorie, fornitori, i 51 articoli, i colori degli smalti), così il modello non spende un passo per chiederla. Lo strumento `struttura_dati` resta disponibile.
- **Prompt affinato** rispetto alla specifica (`prompt_sistema.txt`): cifra principale tra asterischi; "quanto mi costa X" = totale e media al mese, senza corsi e voci che lo nominano soltanto; "quanti X" = quantità, spesa e pezzi per confezione; comprato non vuol dire usato. Da riprovare con il modello di frontiera.
- **Cifra in grande**: è quella che il modello scrive tra asterischi; se manca, il primo importo in euro del testo. Passa comunque dal controllo delle cifre.
- **Controllo delle cifre** (`app/cifre.py`). Una cifra è buona se coincide, a meno di arrotondamento e formato, con: un valore dei risultati (anche dentro un testo, come "conf. 100 pz" o una data); il numero di righe di un risultato; un numero scritto nella domanda o nelle interrogazioni di quella domanda (le costanti che il modello ha messo nel filtro, per esempio il 100 di "confezioni × 100"). I numeri in lettere non si controllano. Una frazione vale come percentuale solo se il numero è seguito da "%".
- **Dopo la riscrittura** il modello può fare altre interrogazioni, dentro il limite di 8 passi. Se la cifra non torna ancora: solo la tabella, con "Ecco i dati, giudicate voi". Se non c'è nessuna tabella: invito a riformulare.
- **Provenienza** (`app/provenienza.py`). Dall'ultima interrogazione si prende la SELECT che legge fatture o righe, se ne tengono tabelle e filtro e si chiede alla base dati quali fatture passano. Per le righe l'importo mostrato è la somma delle righe che contano, non il totale della fattura. Se la risposta viene da `analisi_iniziale`, le fatture sono quelle dei casi di cui il testo nomina il fornitore. Un'interrogazione senza filtro (una percentuale sul totale) mostra tutte le fatture: è vero, anche se poco utile.
- **La provenienza viene dall'interrogazione che contiene la cifra principale**, non per forza dall'ultima. Trovato registrando il video: a "quanto spendo di caffè" l'agente ha guardato prima le capsule (552,00 €) e poi tutto il fornitore (827,50 €), e "Come l'ho calcolato" mostrava le fatture intere del fornitore, che non sommavano alla cifra. Se nessuna interrogazione contiene la cifra, vale l'ultima.
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
- **Ricerca nelle fatture** (zona di sinistra), chiesta da chi presenta per confrontare l'elenco con le risposte: filtra per fornitore o numero di fattura, senza badare a maiuscole e accenti, e mostra quante fatture restano e la loro somma senza IVA. La fattura doppia si vede nell'elenco ma non entra nella somma, come nelle risposte dell'agente. Esc o la × svuotano la ricerca.
- **Lettore della fattura**, chiesto da chi presenta: un clic su una fattura dell'elenco di sinistra, o sul suo numero in "Come l'ho calcolato", la apre in un'altra scheda (`/fattura/<file>`) impaginata come un documento: fornitore, cliente, righe, IVA, totale, scadenza. Gli importi sono quelli scritti nel file, senza cambi di segno; su una nota di credito un avviso spiega che nei conti vale col meno. La fattura doppia ha un avviso con il collegamento all'altro file. Il testo XML sta in fondo, sotto "Il file originale", chiuso.
- **Pagina "Come funziona"** (`/come-funziona`), chiesta da chi presenta: si apre in un'altra scheda da "[ Come funziona ]" in alto a destra. È uno schema in due corsie (prima analisi, domande libere) con quattordici parti cliccabili, tra cui i quattro strumenti dell'agente, ognuno con il nome con cui lo chiama il modello; il pannello a destra spiega ognuna in italiano semplice, con i valori di adesso e, chiusi, i dettagli tecnici (prompt di sistema, strumenti come li vede il modello, tabelle, indirizzo del modello). Niente è scritto a mano nella pagina: modello e limiti vengono da `config.toml`, i numeri dalla base dati e dal registro. Della chiave si dice solo se c'è. Registro, prove e configurazione erano una terza corsia, tolta: la pagina si mostra anche alla sala, e quelle sono cose per chi presenta. Le frecce sinistra e destra passano da una parte all'altra.
- **Il reset non cancella il registro.**

## Replay

- **Cosa si registra**: le tre frasi del modello e il tempo impiegato (`registrazioni/prima_analisi.json`), a ogni prima analisi riuscita. In replay le regole girano davvero, quindi le cifre sono sempre quelle delle fatture caricate.
- **Attivazione**: Opzione+R; un puntino grigio in alto a destra indica che è attivo.
- **La registrazione inclusa** viene dal modello locale usato nello sviluppo: si sostituisce da sola alla prima analisi riuscita con il modello di frontiera.

## Video

- **`./demo video`** registra la demo vera (app accesa, modello vero) in `video/demo_fatture.mp4`, 1920×1080 a 30 fotogrammi al secondo, circa 70 secondi: pagina vuota, caricamento, tre scoperte (avanzando con il pulsante "Prossima scoperta"), cifra finale, una domanda scritta lettera per lettera, risposta e "Come l'ho calcolato" aperto. La domanda predefinita è "Quanto spendo di caffè?"; un'altra si passa come argomento.
- **Contenitore a parte** (`Dockerfile.video`, servizio `video` di `compose.yaml` con profilo dedicato): Chromium, Playwright e ffmpeg servono solo qui, quindi l'immagine dell'app resta leggera e `./demo avvia` non li costruisce. Nessuna dipendenza dalla demo 1.
- **Fotogrammi dallo screencast di Chromium**, montati con ffmpeg secondo i loro tempi: i tempi del video sono quelli veri, compresa l'attesa del modello sulla casella 03.
- **Cursore disegnato nella pagina** (il browser senza interfaccia non ne mostra uno), con traiettorie morbide e un'onda corallo a ogni clic. La cartella si sceglie con un clic sul riquadro: il trascinamento dal Finder non si può simulare.
- **Il video usa la sessione dell'app**: per quel minuto una pagina aperta nel browser mostra la stessa esecuzione. Prima e dopo la registrazione l'app torna allo stato iniziale.
- **L'indirizzo dell'app nella rete dei contenitori è `fatture`**, non `app`: `.app` è un dominio che Chromium apre solo in https.

## Modelli

- **Profilo di frontiera: Claude Sonnet 5.5** (`anthropic:claude@sonnet-5.5`, stesso endpoint compatibile OpenAI della demo 1). Scelto sulla batteria delle 25 domande del 26/11/2026, dopo tre giri di affinamento del prompt:

  | Modello | Giuste su 25 | Tempo medio | Tempo massimo |
  | --- | --- | --- | --- |
  | Sonnet 5.5 | 24 (prima dell'ultimo ritocco: 22, di cui 2 contate male dal giudice) | 7,0 s | 25,7 s |
  | Haiku 5.5 | 21 (nel giro precedente 23) | 4,5 s | 8,3 s |

  In nessun giro, con nessuno dei due, è andata a schermo una cifra sbagliata: le risposte non giuste sono incomplete (manca una cifra secondaria) o, per Haiku, una spesa totale aggiunta alla domanda sul fatturato. Sonnet è più costante nel capire cosa serve; Haiku cambia di più da un giro all'altro. Il prezzo è la velocità: Sonnet ha avuto una domanda a 25,7 secondi (la stessa che negli altri giri ne ha presi 5), oltre il limite di 20. Haiku resta come profilo `haiku` (`PROFILO=haiku ./demo avvia`).
- **Una prova sola per modello non è una misura**: i giri danno risultati diversi (Haiku 19, 23, 21; Sonnet 21, 22, 24, con il prompt che cambiava). Prima del palco conviene ripetere `./demo prova` due o tre volte sul portatile e con la rete della sala.
- **Temperatura**: non viene inviata (`invia_temperatura = false`), perché questi modelli accettano solo quella predefinita. La specifica chiede zero: non è applicabile con questo fornitore.
- **Profilo locale (`gemma4:26b` su Ollama): solo per lo sviluppo, non per il palco.** Sulla batteria: 8 domande giuste su 25 senza "ragionamento" (2–9 secondi a domanda); con il ragionamento acceso 17–33 secondi a domanda, oltre il limite di 20. Il controllo delle cifre impedisce comunque che una cifra inventata vada a schermo, ma troppe domande restano senza una risposta utile. Si attiva con `PROFILO=locale ./demo avvia`.
- **`parametri` nel profilo**: valori in più passati al modello così come sono (per il locale, `reasoning_effort = "none"`).
- **Il giudice della batteria** (`app/cli.py`) segna "giusta" solo se la risposta contiene tutte le cifre attese; accetta i numeri scritti in lettere ("sei fornitori") e la stessa cifra con più decimali (52,43% per 52,4%). "Incompleta" vuol dire che manca una cifra, non che ce ne sia una sbagliata.
- **Riformulazioni e domande fuori dai dati** (sezione 9 della specifica), eseguite il 26/11/2026 con Sonnet 5.5. Le domande stanno in `prove/` e si rilanciano con `./demo riformulazioni` e `./demo fuori`; ogni domanda è indipendente, senza memoria delle precedenti.

  | Prova | Esito | Tempi |
  | --- | --- | --- |
  | 50 riformulazioni (per ogni domanda una formale e una colloquiale o sgrammaticata) | 49 con le cifre attese; la cinquantesima ("i solari presi st'estate") risponde 18 a luglio, che è giusto: la domanda scritta da me restringeva il periodo | 2–10 s |
  | 10 domande fuori dai dati | 10 su 10 dicono chiaramente che il dato non c'è; una aggiunge una cifra non richiesta (la spesa di marzo, vera, alla domanda sugli appuntamenti) | 2–8 s |
  | Batteria delle 25, rifatta dopo l'ultimo ritocco al prompt | 25 su 25 | media 4,8 s, massimo 8,2 s |

- **Cifre di ripiego quando il dato non c'è**: al primo giro, in 6 domande fuori dai dati su 10 l'agente aggiungeva una cifra "vicina" (l'IVA pagata a chi chiedeva delle tasse, il prezzo della cera a chi chiedeva il prezzo della ceretta). Erano cifre vere, ma non richieste e facili da fraintendere dal vivo. Ora il prompt le vieta, con una sola eccezione: se chiedono un costo e nelle fatture ce n'è una parte (per i dipendenti, l'elaborazione delle buste paga), la dà dicendo cos'è e cosa manca.
- **Il giudice per le domande fuori dai dati** cerca una frase che dica che il dato non c'è e segnala a parte gli importi aggiunti. È un controllo sul testo: le risposte vanno comunque lette nel resoconto.
