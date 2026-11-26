# Demo 2 – Le fatture che parlano

Applicazione dimostrativa per un intervento dal vivo a CNA Latina (artigiani e piccole imprese, non tecnici). Chi presenta trascina una cartella con le 196 fatture elettroniche ricevute in un anno da un centro estetico inventato (Brezza Estetica S.r.l.); l'app le legge, mostra tre scoperte con una cifra finale di soldi recuperabili (2.733,66 €) e poi risponde a domande libere del pubblico, mostrando da dove viene ogni cifra. Dura 6 minuti, gira su un portatile (Apple M4 Pro, 48 GB, macOS).

**Stato:** l'applicazione è costruita e gira in Docker (`./demo avvia`, porta 8002). I test automatici passano; la batteria delle 25 domande va ancora eseguita con il modello di frontiera (serve la chiave in `.env`). Comandi e struttura in `README.md`, scelte in `DECISIONI.md`.

## Dove sta cosa

`contesto/` è il materiale ricevuto da chi presenta: è la fonte di verità e non va modificato (vedi `contesto/CLAUDE.md`).

| Quando lavori a… | Leggi |
| --- | --- |
| Qualsiasi cosa, la prima volta | `contesto/LEGGIMI.md` (compito, consegne, ordine di lavoro) |
| Caricamento XML, tabelle, convenzioni | `contesto/docs/SPECIFICA.md` §3 e `contesto/strumenti/carica_fatture.py` |
| Le quattro regole della prima analisi | SPECIFICA §4 e §5.2, `contesto/strumenti/risposte_attese.py` |
| Strumenti dell'agente, controllo delle cifre, provenienza | SPECIFICA §5.3 |
| Pagina, schede, grafici, stile | SPECIFICA §6 e `contesto/docs/slide_46.png` |
| Prompt di sistema | SPECIFICA §7 |
| Batteria delle 25 domande | SPECIFICA §8 e `contesto/dati/domande_di_prova.json` |
| Test di accettazione, replay, reset | SPECIFICA §9 |
| Copione di chi presenta | SPECIFICA §10 |

Se questo file e la specifica divergono, vale la specifica.

## Decisioni già prese: non rimetterle in discussione

1. **Domande libere**, scritte a mano. Nessun pulsante con domande pronte.
2. **Le cifre vengono solo dai risultati delle interrogazioni**, mai dal modello. Il codice controlla ogni numero del testo prima di mostrarlo; se non torna, una riscrittura, poi solo la tabella con "ecco i dati, giudicate voi".
3. **La prima analisi è fatta da regole fisse**; il modello scrive solo le frasi. Le cifre delle tre scoperte e del totale le mette il codice.
4. **Ogni risposta mostra "Come l'ho calcolato"**, con le fatture coinvolte (fornitore, numero, data, importo).
5. **Base dati in sola lettura** per l'agente: solo `SELECT`, limite 5 secondi, massimo 200 righe.
6. **Applicazione indipendente** dalla demo 1 (`../1`): nessuna dipendenza, nessun codice condiviso o copiato, aspetto proprio.
7. **Tutto in locale**, senza risorse da internet (niente CDN, font o librerie remote). L'unica chiamata di rete è quella al modello.
8. **Meglio "non c'è" che una cifra inventata**: nelle fatture ci sono solo gli acquisti.
9. **Interfaccia in italiano**, senza termini tecnici a schermo, corpo minimo 20 px, importi nel formato `1.234,56 €`.
10. **Il nome dell'impresa è provvisorio**: sta in configurazione, mai scritto nel codice.

## Convenzioni sui dati

- **Spesa = imponibile**, IVA esclusa, salvo richiesta esplicita del totale con IVA.
- **Note di credito (`TD04`) col segno meno**, importi e quantità.
- **Doppioni marcati, non cancellati** (`doppione = 1`). Ogni analisi parte dalle viste `fatture_valide` e `righe_valide`.
- **Articolo = descrizione della riga.** Solo per gli smalti la parte dopo ` – ` è il colore e va in `variante`.
- Categoria e regione vengono da `contesto/dati/fornitori.csv`, abbinato per partita IVA.

## Numeri di controllo

196 file → 195 fatture valide + 1 doppione · 19 fornitori · 16 categorie · 500 righe valide · 67.808,52 € di imponibile · 14.143,37 € di IVA · 81.951,89 € con IVA.

Recuperabile: 1.331,50 (fattura doppia) + 1.040,00 (canone dopo il ritiro) + 254,66 (aumenti) + 107,50 (gel) = **2.733,66 €**.

Tutti gli altri numeri attesi stanno in `contesto/dati/risposte_attese.json`: i test automatici li leggono da lì, non li riscrivono a mano.

## Trappole già note

- "500 righe" sono le righe **valide**: la tabella `righe` ne ha 504, perché include le 4 del doppione.
- Il periodo dichiarato è 01/11/2025–31/10/2026, ma l'ultima fattura è del 28/10/2026.
- La regola degli aumenti va limitata alle righe **con unità di misura**: altrimenti escono le commissioni sulle carte, che cambiano ogni mese. Con il filtro trova cera, crema massaggio e anche la luce (kWh): la luce si mostra ma resta **fuori** dal totale recuperabile.
- La radice dell'XML ha il prefisso `p:`, gli elementi interni non hanno spazio dei nomi. Una fattura può avere più `DatiRiepilogo` (le commissioni sulle carte sono esenti, `Natura` N4).
- Il separatore nelle descrizioni è un trattino medio (`–`), non il trattino semplice.
- Percentuali, medie, differenze e moltiplicazioni (confezioni × pezzi) vanno fatte **nell'interrogazione**, altrimenti non passano il controllo delle cifre.

## Come si lavora qui

- **Tutto gira nel contenitore.** `./demo test` per i test, `./demo prova [numeri]` per la batteria, `./demo domanda "..."` per una domanda sola, `./demo riavvia` dopo una modifica a `config.toml`. Il codice in `app/` è montato nel contenitore: una modifica a Python vuole `./demo riavvia`, una alla pagina si vede ricaricando.
- **Sviluppo senza spendere**: `PROFILO=locale ./demo avvia` usa il modello locale su Ollama. Serve solo a provare la pagina: sulla batteria fa 8 su 25, i giudizi sul prompt si danno con il modello di frontiera.
- **Per guardare la pagina** serve un browser vero a 1920×1080; il caricamento si prova scegliendo la cartella `contesto/dati/fatture` dal riquadro di sinistra.

- **Verifica del pacchetto** (deve dare un file identico a `contesto/dati/risposte_attese.json`):
  ```
  python3 contesto/strumenti/risposte_attese.py contesto/dati/fatture contesto/dati/fornitori.csv /tmp/fatture.db /tmp/verifica.json
  ```
- **Ogni scelta non coperta dalla specifica va annotata in `DECISIONI.md`**, nella sezione giusta.
- **Moduli separati e riconoscibili** per collegamento al modello, configurazione e stile: in futuro potrebbero finire in una cartella comune alle due demo.
- **Modello**: protocollo compatibile OpenAI con chiamata di strumenti, temperatura zero. Indirizzo, chiave e nome stanno nel file di configurazione, che non va nel repository (va versionato solo un esempio senza chiave).
- **Limiti per domanda**: 8 passi, 3 tentativi di interrogazione. Ogni domanda, interrogazione e risultato finisce nel file di registro.
- **Finito** significa: superati i test di accettazione della SPECIFICA §9. Quelli che richiedono il portatile del palco, il modello locale o il proiettore li esegue chi presenta: lasciare istruzioni chiare.
