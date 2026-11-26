# Demo 2 – Le fatture che parlano

Leggi questo file per primo. Poi `docs/SPECIFICA.md`, che è il documento di riferimento.

## Il compito

Costruisci un'applicazione dimostrativa a sé, in un repository proprio, che gira interamente su un portatile (Apple M4 Pro, 48 GB, macOS). Chi presenta trascina una cartella con le fatture elettroniche ricevute in un anno da un centro estetico; l'app le legge, mostra tre scoperte con una cifra finale di soldi recuperabili, e poi **risponde a domande libere** scritte da chi presenta su richiesta del pubblico.

Esiste una demo 1, costruita a parte, su un altro scenario (un grossista che prepara un preventivo). **Questa applicazione non ne dipende e non ne condivide codice.** Sul palco chi presenta chiude la prima, cambia finestra e si sposta: il cambio di scenario deve vedersi.

## Il contesto

È la seconda di due dimostrazioni dal vivo in un intervento per CNA Latina, davanti ad artigiani e piccole imprese, non tecnici. Dura 6 minuti e serve a mostrare una riduzione dei costi. La demo 1 mostra un agente che prepara un documento e aspetta l'ok; questa mostra un agente che guarda dentro dati che ogni impresa possiede e nessuno legge.

Il momento che conta è quando qualcuno in sala fa una domanda qualsiasi sulle fatture e l'agente risponde con una cifra vera, mostrando da dove viene. Per questo le domande non sono preimpostate.

## Cosa c'è nel pacchetto

| Percorso | Contenuto | Come usarlo |
| --- | --- | --- |
| `docs/SPECIFICA.md` | Specifica completa | Documento di riferimento |
| `docs/slide_46.png` | Una slide dell'intervento | Riferimento per la famiglia grafica (caratteri, etichette, fondo); l'app ha però un colore d'accento e un impianto propri |
| `dati/fatture/` | 196 fatture elettroniche XML (FatturaPA, FPR12) | La cartella che chi presenta trascina nell'app |
| `dati/fornitori.csv` | Categoria e regione di ogni fornitore, per partita IVA | Usato al caricamento |
| `dati/risposte_attese.json` | Tutti i numeri attesi: totali, categorie, storie, curiosità | Base per i test automatici |
| `dati/domande_di_prova.json` | 25 domande con le cifre che la risposta deve contenere | Batteria di prova dell'agente |
| `strumenti/carica_fatture.py` | Lettura degli XML e creazione della base dati | Implementazione di riferimento, funzionante |
| `strumenti/risposte_attese.py` | Calcolo dei numeri attesi dalla base dati | Mostra come si ottiene ogni cifra |
| `strumenti/genera_fatture.py` | Il generatore delle fatture inventate | Solo se serve rigenerare o adattare i dati |

Per verificare il pacchetto:

```
python3 strumenti/risposte_attese.py dati/fatture dati/fornitori.csv /tmp/fatture.db /tmp/verifica.json
```

Il risultato deve coincidere con `dati/risposte_attese.json`.

## Decisioni già prese: non rimetterle in discussione

1. **Domande libere**, scritte a mano. Nessun pulsante con domande pronte.
2. **Le cifre vengono solo dai risultati delle interrogazioni.** Il codice controlla ogni numero prima di mostrarlo.
3. **La prima analisi è fatta da regole fisse**; il modello la racconta. Le cifre delle tre scoperte le mette il codice.
4. **Ogni risposta mostra "Come l'ho calcolato"**, con le fatture coinvolte.
5. **Base dati in sola lettura** per l'agente.
6. **Applicazione indipendente**, con aspetto proprio, in un repository separato dalla demo 1.
7. **Tutto in locale**, senza risorse da internet. L'unica connessione esterna è quella al modello.
8. **Le convenzioni sui dati** della sezione 3 della specifica: spesa = imponibile, note di credito negative, doppioni marcati ed esclusi dalle viste.
9. **Dati e numeri sono validati**: 196 file, 67.808,52 € di imponibile, 2.733,66 € recuperabili.
10. **Interfaccia in italiano**, senza termini tecnici a schermo.
11. **Impresa, fornitori, partite IVA e prezzi sono inventati.** Il nome dell'impresa è provvisorio: tienilo in configurazione.

## Scelte lasciate a te

- Linguaggio e librerie. Suggerimento: Python, perché gli script di riferimento sono già scritti così; la base dati di riferimento è SQLite.
- Il colore d'accento e i dettagli dell'aspetto, dentro i limiti della sezione 6.
- La struttura del progetto. Tieni separati in moduli riconoscibili il collegamento al modello, la configurazione e lo stile: sono le parti che in futuro potrebbero finire in una cartella comune alle due demo.
- La libreria per i grafici, purché inclusa nell'app.
- Come realizzare il controllo delle cifre e la ricostruzione della provenienza.

Annota le scelte non coperte dalla specifica in `DECISIONI.md`.

## Cosa consegnare

1. L'applicazione, avviabile con un solo comando, con istruzioni di installazione per macOS e caricamento delle fatture per trascinamento.
   Un file di configurazione con modello (indirizzo, chiave, nome) e dati dell'impresa.
2. Le quattro regole della prima analisi, con test automatici sui numeri attesi.
3. I quattro strumenti dell'agente e il controllo delle cifre.
4. Uno script che lancia le 25 domande di prova, confronta le cifre e scrive un resoconto.
5. Reset dell'applicazione e replay della prima analisi.
6. Il registro di domande, interrogazioni e risultati.

## Ordine di lavoro consigliato

1. Caricamento degli XML e test sui totali.
2. Le quattro regole e il totale recuperabile.
3. Strumenti dell'agente e ciclo delle domande, provati da riga di comando con la batteria.
4. Controllo delle cifre e provenienza.
5. La pagina: caricamento, tre scoperte, schede delle risposte, grafici.
6. Reset, replay, gestione degli errori.

## Quando è finito

Quando supera i test di accettazione della sezione 9 della specifica. Quelli che richiedono il portatile del palco, il modello locale o il proiettore li esegue chi presenta: lascia istruzioni chiare su come lanciarli.
