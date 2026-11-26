# Demo 2 – Le fatture che parlano: specifica di realizzazione

Versione del 25/11/2026. Tutto ciò che è scritto qui è stato validato con chi presenta la demo.

## 1. Obiettivo e vincoli

La demo dura 6 minuti e deve far vedere una cosa sola: un agente legge tutte insieme le fatture di un anno e trova soldi che nessuno aveva visto. Poi risponde alle domande che arrivano dalla sala. Il pubblico è lo stesso della demo 1: artigiani e piccole imprese di CNA Latina, non tecnici.

Cinque vincoli guidano ogni scelta:

- **Domande libere.** Chi presenta scrive le domande così come arrivano dal pubblico. Niente pulsanti con domande già pronte.
- **I numeri vengono dalle fatture, mai dal modello.** Il modello scrive un'interrogazione sui dati; il codice la esegue; le cifre mostrate sono quelle del risultato.
- **Ogni risposta mostra da dove viene.** Sotto ogni cifra, le fatture o le righe che la compongono.
- **Meglio "non c'è" che una cifra inventata.** Nelle fatture passive ci sono gli acquisti: niente vendite, stipendi o incassi.
- **Tutto in locale.** Fatture, tabella e grafici stanno sul portatile, senza risorse da internet. L'unica chiamata di rete è quella al modello.

La demo è un'applicazione a sé, in un repository separato da quello della demo 1, con cui non condivide codice. Sul palco si cambia finestra e ci si sposta: il pubblico deve capire a colpo d'occhio che è un altro scenario. Usa il modello di frontiera; il modello si imposta in un file di configurazione, senza menu a schermo.

## 2. Scenario

Un centro estetico di Latina carica le fatture ricevute in un anno: 196 file, 19 fornitori, 67.808,52 € di spesa IVA esclusa.

| Elemento | Scelta |
| --- | --- |
| Impresa | Brezza Estetica S.r.l., centro estetico a Latina con tre dipendenti. Impresa inventata; nome provvisorio, da tenere in configurazione. |
| Periodo | Dal 1° novembre 2025 al 31 ottobre 2026. |
| Fatture | 196 file XML, di cui 195 fatture distinte e 1 doppione. Una è una nota di credito. |
| Fornitori | 19, tutti inventati: 10 in provincia di Latina, gli altri tra Roma, Napoli, Firenze, Bologna, Milano e Torino. |
| Spesa | 67.808,52 € di imponibile, 81.951,89 € con IVA. In media 5.650,71 € al mese. |

Le 16 categorie di spesa, assegnate per fornitore nel file `dati/fornitori.csv`:

| Categoria | Spesa (€, IVA esclusa) | Quota |
| --- | --- | --- |
| Affitto | 16.800,00 | 24,8% |
| Noleggio macchinari | 12.344,00 | 18,2% |
| Prodotti per trattamenti | 5.821,86 | 8,6% |
| Energia e acqua | 4.798,36 | 7,1% |
| Software e incassi | 4.432,00 | 6,5% |
| Prodotti per rivendita | 4.164,70 | 6,1% |
| Unghie | 3.886,90 | 5,7% |
| Consulenze | 2.928,00 | 4,3% |
| Lavanderia | 2.888,90 | 4,3% |
| Pulizie | 2.640,00 | 3,9% |
| Monouso e consumabili | 2.479,90 | 3,7% |
| Pubblicità | 2.010,00 | 3,0% |
| Formazione | 950,00 | 1,4% |
| Accoglienza clienti | 827,50 | 1,2% |
| Telefonia e internet | 656,40 | 1,0% |
| Manutenzioni | 180,00 | 0,3% |

## 3. Dati

Le fatture sono file XML nel tracciato della fattura elettronica italiana (FatturaPA, formato FPR12), uno per fattura, nella cartella `dati/fatture`. La struttura segue il tracciato, ma i file non sono stati validati con lo schema ufficiale e non sono firmati. L'elemento radice ha il prefisso di spazio dei nomi `p:`; gli elementi interni non hanno spazio dei nomi.

Campi letti da ogni file:

| Dato | Dove sta nel file |
| --- | --- |
| Fornitore, partita IVA, sede | `FatturaElettronicaHeader/CedentePrestatore` |
| Tipo, numero, data, totale, causale | `FatturaElettronicaBody/DatiGenerali/DatiGeneraliDocumento` (`TD01` fattura, `TD04` nota di credito) |
| Righe: descrizione, quantità, unità, prezzo, importo, IVA | `DatiBeniServizi/DettaglioLinee` |
| Imponibile e imposta | `DatiBeniServizi/DatiRiepilogo` (può essercene più di uno per fattura; le commissioni sulle carte sono esenti, con `Natura` N4 e aliquota 0) |
| Scadenza di pagamento | `DatiPagamento/DettaglioPagamento/DataScadenzaPagamento` |

Al caricamento il codice costruisce una base dati locale con due tabelle. È tutto ciò che l'agente può interrogare.

| Tabella | Una riga per | Colonne principali |
| --- | --- | --- |
| `fatture` | Fattura | file, fornitore, partita_iva, comune, provincia, regione, categoria, tipo_documento, numero, data, mese, imponibile, iva, totale, scadenza, giorni_pagamento, causale, doppione |
| `righe` | Riga di fattura | fattura_id, fornitore, categoria, data, mese, descrizione, articolo, variante, quantita, unita, prezzo_unitario, importo, aliquota_iva, doppione |

Quattro convenzioni, le stesse su cui sono calcolati i numeri attesi:

1. **Spesa = imponibile**, IVA esclusa, salvo che la domanda chieda il totale con IVA.
2. **Note di credito col segno meno**: importi e quantità di un `TD04` sono negativi.
3. **Doppioni marcati, non cancellati**: un file con stesso fornitore, numero, data e totale di uno già caricato ha `doppione = 1`. Le viste `fatture_valide` e `righe_valide` li escludono, e ogni analisi parte da quelle.
4. **Articolo e variante**: l'articolo è la descrizione della riga. Solo per gli smalti la parte dopo il trattino è il colore e finisce in `variante`.

Categoria e regione vengono da `dati/fornitori.csv`, abbinato per partita IVA. Lo script `strumenti/carica_fatture.py` è un'implementazione di riferimento funzionante di tutto questo: si può integrare così com'è o riscrivere, purché produca gli stessi numeri.

## 4. Le storie nascoste nei dati

Nelle fatture ci sono 2.733,66 € da recuperare o risparmiare, più due aumenti che continueranno a pesare. Tutti i numeri sono calcolati rileggendo gli XML e stanno in `dati/risposte_attese.json`.

Le quattro storie che compongono la cifra finale:

| Storia | Cosa c'è nei dati | Cifra (€, IVA esclusa) |
| --- | --- | --- |
| Fattura doppia | La fattura 2025-330 di Dermovita Cosmetici dell'11/11/2025 compare in due file identici (`IT09999000117_00001.xml` e `IT09999000117_00002.xml`) | 1.331,50 |
| Canone dopo il ritiro | TecnoBeauty Noleggi ritira la pressoterapia il 03/06/2026 (riga "Ritiro apparecchiatura a fine noleggio") ma fattura il canone da 260,00 € anche a luglio, agosto, settembre e ottobre | 1.040,00 |
| Aumenti a piccoli passi | Linea Pelle Distribuzione alza in 7 ritocchi la cera (da 9,80 a 11,27 €, +15,0%) e la crema massaggio (da 12,50 a 14,40 €, +15,2%) | 254,66 già pagati in più |
| Stesso gel, due prezzi | Il gel costruttore da 50 ml costa 24,00 € da Nail Point Italia e 28,30 € da Beauty Pro Forniture (+17,9%); 25 pezzi comprati al prezzo alto | 107,50 |
| **Totale** | | **2.733,66** |

Come si calcolano: la fattura doppia vale il suo imponibile; il canone dopo il ritiro è la somma dei canoni con data successiva al ritiro; gli aumenti sono la somma, riga per riga, di quantità × (prezzo pagato − primo prezzo); il gel è pezzi comprati al prezzo alto × differenza di prezzo.

Due aumenti che pesano sul futuro, da mostrare ma fuori dal totale:

- **Prodotti.** Ai prezzi di ottobre, cera e crema costano 603,93 € l'anno in più rispetto ai prezzi di partenza.
- **Luce.** Da luglio 2026 il prezzo passa da 0,212 a 0,268 € al kWh (+26,4%). In quattro mesi sono 377,44 € in più; sui 16.710 kWh dell'anno sarebbero circa 936 €.

Le storie pensate per le domande curiose:

| Argomento | Cosa si scopre |
| --- | --- |
| Laser a noleggio | 9.144,00 € l'anno, 762,00 € al mese tra canone, manutenzione e gel |
| Incassare e prendere appuntamenti | 4.432,00 €: 3.290,00 di commissioni sulle carte, 180,00 di canone POS, 588,00 di gestionale, 374,00 di SMS |
| Smalti | 314 boccette in un anno; il colore più comprato è Nude Rosa (82), poi Rosso Ciliegia (69); il meno comprato Blu Notte (3) |
| Caffè per i clienti | 23 confezioni, cioè 2.300 capsule, per 552,00 € |
| Cera | 279 barattoli, 2.904,31 € |
| Lavanderia | 1.295 kg di teli e asciugamani, 2.888,90 € |
| Natale | 55 cofanetti regalo comprati, 8 resi a gennaio con nota di credito da 176,00 € |
| Vicino a casa | 52,4% della spesa in provincia di Latina, 62,4% nel Lazio |
| Pagamenti | 6 fornitori vogliono il pagamento alla data della fattura; Beauty Pro e Dermovita concedono 60 giorni |
| Mesi | Il più caro è settembre 2026 (6.628,18 €), il meno caro gennaio 2026 (4.551,92 €) |

Avvertenza: cercando "articoli il cui prezzo è cambiato" escono anche le commissioni sulle carte, che variano ogni mese perché dipendono dagli incassi. La ricerca degli aumenti va limitata alle righe con unità di misura.

## 5. Architettura e strumenti

La demo ha due momenti costruiti in modo diverso: la prima analisi è fatta da regole fisse e il modello la racconta; le domande libere passano da interrogazioni scritte dal modello ed eseguite dal codice.

**1. Caricamento.** Chi presenta trascina la cartella. Il codice legge i 196 file, costruisce le due tabelle e marca i doppioni. Nessun modello coinvolto. Deve durare meno di 5 secondi; a schermo l'avanzamento va rallentato perché si veda.

**2. Prima analisi.** Il codice applica quattro regole e ne passa i risultati al modello, che li racconta in tre scoperte (dove vanno i soldi, chi ha alzato i prezzi, cosa non torna):

| Regola | Cosa cerca |
| --- | --- |
| Doppioni | File con stesso fornitore, numero, data e totale |
| Aumenti | Stesso articolo e stesso fornitore, righe con unità di misura, prezzo finale superiore a quello iniziale di almeno il 5% |
| Stesso articolo, prezzi diversi | Stesso articolo comprato da fornitori diversi con prezzi che differiscono di almeno il 5% |
| Canoni dopo la fine | Una riga che contiene "ritiro", "fine noleggio", "disdetta" o "cessazione", seguita da canoni dello stesso fornitore in date successive |

Le cifre delle tre scoperte e del totale le mette il codice nelle schede; il modello scrive solo le frasi di accompagnamento.

**3. Domande libere.** Il modello ha quattro strumenti:

| Strumento | Argomenti | Restituisce |
| --- | --- | --- |
| `struttura_dati` | nessuno | Tabelle, colonne, convenzioni, elenco di categorie e fornitori, periodo coperto |
| `analisi_iniziale` | nessuno | I risultati delle quattro regole, per rispondere a domande che li riguardano |
| `interroga` | un'interrogazione SQL di sola lettura | Le righe del risultato, al massimo 200 |
| `mostra_grafico` | tipo (barre o linea), titolo, interrogazione che restituisce etichetta e valore | Niente: il codice esegue l'interrogazione e disegna il grafico |

Regole di implementazione:

- `interroga` apre la base dati in sola lettura, accetta solo `SELECT` e ha un limite di 5 secondi. Un errore torna al modello come testo, così può correggersi; al massimo 3 tentativi per domanda.
- **Controllo delle cifre.** Prima di mostrare una risposta, il codice verifica che ogni numero nel testo compaia nei risultati degli strumenti di quella domanda, a meno di arrotondamento e formato. Se una cifra non torna, chiede al modello di riscrivere una volta; se non torna ancora, mostra solo la tabella del risultato con la dicitura "ecco i dati, giudicate voi".
- **Calcoli derivati.** Percentuali, medie e differenze vanno fatte nell'interrogazione, non a mente dal modello, così passano il controllo.
- **Provenienza.** Per "Come l'ho calcolato" il codice conserva l'ultima interrogazione e ne ricava le fatture coinvolte (fornitore, numero, data, importo).
- Il grafico usa una libreria inclusa nell'app, senza risorse da internet.
- Ogni domanda, interrogazione e risultato va scritto nel file di registro.
- Limite di 8 passi per domanda, poi messaggio chiaro e possibilità di riformulare.
- Il modello si raggiunge con un protocollo compatibile OpenAI con chiamata di strumenti. Indirizzo, chiave e nome del modello stanno in un file di configurazione, insieme ai dati dell'impresa. Il formato del file ricalca quello della demo 1, così in futuro le parti comuni si possono spostare in una cartella condivisa; per ora niente dipendenze tra i due repository.

## 6. Schermate

Una pagina a tutto schermo, 1920×1080, a tre zone, con un aspetto proprio: è l'applicazione di Brezza Estetica, non quella del grossista. Resta nella famiglia grafica dell'intervento (fondo chiaro, etichette in carattere monospaziato, titoli grandi; vedi `docs/slide_46.png`), ma cambia il colore d'accento, per esempio un corallo al posto del blu-viola, e cambia l'impianto: qui il centro della pagina è una conversazione. Il verde lime resta riservato alla cifra trovata.

| Zona | Contenuto |
| --- | --- |
| Sinistra: le fatture | All'inizio un riquadro "Trascina qui la cartella delle fatture". Dopo il caricamento: contatore dei file letti, periodo, numero di fornitori, elenco scorrevole delle fatture. |
| Centro: la conversazione | Le risposte dell'agente, una scheda per domanda. In basso il campo per scrivere, sempre attivo, con corpo grande. |
| Destra: trovato finora | Una sola cifra grande su fondo verde lime: il totale recuperabile. Sotto, le voci che lo compongono. |

Durante il caricamento, al centro compaiono tre caselle numerate:

| Casella | Titolo | Riga a lavoro fatto |
| --- | --- | --- |
| 01 | Legge le fatture | "196 file, da novembre 2025 a ottobre 2026." |
| 02 | Le mette in ordine | "19 fornitori, 500 righe, 16 voci di spesa." |
| 03 | Cerca cosa non torna | "Ho trovato 4 cose da guardare." |

La scheda di una risposta ha quattro parti:

1. **La domanda**, così com'è stata scritta.
2. **La risposta in una frase**, con la cifra principale in grande.
3. **Un grafico**, solo quando aiuta: un andamento nel tempo o un confronto tra più di tre voci.
4. **"Come l'ho calcolato"**, richiudibile: in italiano semplice cosa ha cercato, poi le fatture o le righe da cui viene la cifra, con fornitore, numero e data. Le prime 10 sono visibili, le altre a scorrimento.

Requisiti:

- La prima analisi mostra tre schede, una per scoperta: dove vanno i soldi, chi ha alzato i prezzi, cosa non torna.
- La cifra a destra parte da zero e sale mentre compaiono le scoperte, fino a 2.733,66 €.
- Mentre l'agente lavora a una domanda, la scheda mostra cosa sta facendo in parole semplici ("Sto guardando le fatture della luce"), non l'interrogazione.
- Corpo minimo 20 px, nessun termine tecnico a schermo. L'interrogazione SQL compare solo nel pannello "dettagli tecnici", chiuso di default.
- Se la domanda riguarda cose che nelle fatture non ci sono, la scheda lo dice e suggerisce cosa invece si può chiedere.
- Importi in formato italiano: 1.234,56 €.

## 7. Prompt di sistema

Punto di partenza da affinare con la batteria di domande di prova. Lo stesso per i due profili di modello.

```
Sei l'assistente di Brezza Estetica S.r.l., un centro estetico di
Latina. Hai davanti le fatture ricevute dai fornitori in un anno e
rispondi alle domande della titolare su queste fatture.

Cosa hai a disposizione:
- Solo le fatture d'acquisto. Non conosci vendite, incassi, clienti,
  stipendi, margini, né nulla che non sia scritto in una fattura.
- Due tabelle, da leggere sempre dalle viste fatture_valide e
  righe_valide. Usa struttura_dati se non ricordi colonne o valori.

Come rispondi:
1. Per ogni domanda scrivi un'interrogazione con interroga. Non
   rispondere mai a memoria e non stimare.
2. Fai fare i conti all'interrogazione: somme, medie, percentuali e
   differenze. Non calcolare a mente.
3. Riporta solo cifre che compaiono nei risultati. Se un risultato è
   vuoto, dillo.
4. "Spesa" significa imponibile, IVA esclusa, a meno che chiedano
   il totale con IVA.
5. Le descrizioni dei fornitori non sempre usano le parole della
   domanda: cerca per parti di parola e, se non trovi, guarda quali
   articoli e categorie esistono prima di dire che non c'è.
6. Se la domanda riguarda aumenti, doppioni, noleggi finiti o prezzi
   diversi tra fornitori, guarda prima analisi_iniziale.
7. Usa mostra_grafico solo per andamenti nel tempo o confronti tra
   più di tre voci.

Se la domanda è ambigua, scegli la lettura più probabile e dilla in
mezza frase. Se chiedono qualcosa che nelle fatture non c'è, dillo
chiaramente e proponi una domanda vicina a cui puoi rispondere.

Stile: una o due frasi, in italiano semplice, con la cifra
principale all'inizio. Importi in euro con due decimali. Niente
termini tecnici, niente nomi di tabelle o colonne. Non dare consigli
fiscali o legali: segnala e lascia decidere.
```

## 8. Domande di prova

Venticinque domande che un artigiano potrebbe fare davvero, con la risposta che i dati impongono. Sono anche in `dati/domande_di_prova.json`, con le cifre da ritrovare nella risposta. Importi IVA esclusa.

| # | Domanda | Risposta attesa |
| --- | --- | --- |
| 1 | Quanto ho speso in tutto? | 67.808,52 € |
| 2 | Qual è la mia spesa più grande? | Affitto: 16.800,00 €, il 24,8% |
| 3 | Quanto mi costa il laser? | 9.144,00 € l'anno, 762,00 € al mese |
| 4 | Quanto pago la luce? | 4.375,96 € per 16.710 kWh; il mese più caro è agosto 2026 |
| 5 | Chi mi ha alzato i prezzi? | Linea Pelle: cera +15,0%, crema massaggio +15,2%. Luce: +26,4% da luglio 2026 |
| 6 | C'è qualcosa che pago due volte? | Fattura Dermovita 2025-330 dell'11/11/2025, 1.331,50 €, presente due volte |
| 7 | Pago qualcosa che non uso più? | Pressoterapia: ritirata il 03/06/2026, 4 canoni successivi, 1.040,00 € |
| 8 | Compro la stessa cosa da più fornitori? | Gel costruttore: 24,00 € da Nail Point, 28,30 € da Beauty Pro |
| 9 | Quanti smalti ho comprato quest'anno? | 314 boccette, 2.166,60 € |
| 10 | Di che colore ne compro di più? | Nude Rosa, 82 boccette |
| 11 | Quanto caffè offriamo ai clienti? | 23 confezioni da 100 capsule: 2.300 capsule, 552,00 € |
| 12 | Quanto mi costa incassare con le carte? | 3.470,00 €: 3.290,00 di commissioni e 180,00 di canone POS |
| 13 | Quanto spendo in lavanderia? | 2.888,90 €, per 1.295 kg di teli e asciugamani più il noleggio accappatoi |
| 14 | Quanto compro in provincia di Latina? | 35.552,66 €, il 52,4%, da 10 fornitori |
| 15 | Chi vuole essere pagato subito? | Sei fornitori: Accademia Estetica Avanzata, AgendaBella, MedLaser Rent, Nail Point Italia, PagoFacile, TecnoBeauty Noleggi |
| 16 | Qual è stato il mese più caro? | Settembre 2026: 6.628,18 € |
| 17 | Quanti barattoli di cera ho usato? | 279 comprati |
| 18 | Ho ricevuto note di credito? | Una: Dermovita, 20/01/2026, 176,00 € per 8 cofanetti resi |
| 19 | Quanto ho speso in formazione? | 950,00 € per due corsi, a marzo e settembre 2026 |
| 20 | Quanti solari ho comprato? | 54, tra maggio e luglio 2026 |
| 21 | Quanta IVA ho pagato? | 14.143,37 € |
| 22 | Quanti guanti ho comprato? | 93 confezioni da 100: 9.300 guanti, 520,80 € |
| 23 | Da chi ricevo più fatture? | Centro Servizi Contabili Latina: 16 |
| 24 | Quanto ho fatturato quest'anno? | Non c'è: nelle fatture ricevute ci sono solo gli acquisti |
| 25 | Quanto mi costano i dipendenti? | Gli stipendi non ci sono. C'è solo l'elaborazione delle buste paga: 1.008,00 € |

Tre casi chiedono attenzione particolare:

- **La 17** dice "usato", ma le fatture dicono "comprato". La risposta giusta fa notare la differenza in mezza frase.
- **La 11 e la 22** chiedono di moltiplicare le confezioni per i pezzi scritti nella descrizione. Il calcolo va fatto nell'interrogazione.
- **La 24 e la 25** verificano che l'agente sappia dire "non c'è".

## 9. Test di accettazione e affidabilità

La demo è pronta quando supera tutti i test qui sotto sul portatile che andrà sul palco.

- [ ] **Caricamento.** I 196 file diventano 195 fatture valide e 1 doppione, 500 righe, 19 fornitori, 67.808,52 € di imponibile. Test automatico confrontato con `dati/risposte_attese.json`.
- [ ] **Prima analisi.** Le quattro regole trovano le quattro storie con le cifre attese; il totale a destra è 2.733,66 €. 10 esecuzioni su 10.
- [ ] **Domande di prova.** Con il modello di frontiera, almeno 23 delle 25 domande danno la cifra attesa al primo tentativo, e nessuna dà una cifra sbagliata presentata come certa.
- [ ] **Riformulazioni.** Ogni domanda di prova regge almeno due modi diversi di chiederla, compreso uno sgrammaticato o colloquiale.
- [ ] **Controllo delle cifre.** Forzando una risposta con un numero inventato, la scheda non lo mostra.
- [ ] **Fuori dai dati.** Dieci domande su cose che non stanno nelle fatture: l'agente dice che non c'è, dieci volte su dieci.
- [ ] **Sola lettura.** Un'interrogazione che prova a modificare o cancellare viene rifiutata.
- [ ] **Tempi.** Caricamento entro 5 secondi; prima analisi entro 30; una domanda libera entro 20.
- [ ] **Indipendenza.** L'applicazione si installa e parte da sola, su un portatile dove la demo 1 non c'è.
- [ ] **Reset.** Un comando riporta l'applicazione allo stato iniziale, senza fatture caricate.
- [ ] **Proiettore.** Cifre, grafici e "come l'ho calcolato" leggibili dall'ultima fila.

Rete di sicurezza per il palco:

- **Replay della prima analisi**, attivabile da tastiera: ripropone un'esecuzione riuscita con gli stessi tempi, senza chiamare il modello.
- **Uno script di prova** che lancia le 25 domande, confronta le cifre e scrive un resoconto: dice quali tipi di domanda il modello sbaglia.
- **Temperatura a zero.**
- **Video di riserva** della demo completa, con tre domande libere (lo registra chi presenta).

## 10. Per chi presenta

La prima metà è garantita dai dati; la seconda è libera, e va presentata come tale.

### Copione, 6 minuti

| Tempo | A schermo | Cosa dire |
| --- | --- | --- |
| 0:00–0:45 | Altra finestra, altra applicazione: pagina vuota, cartella sul desktop | "Cambiamo mestiere: un centro estetico di Latina, inventato. Questa cartella sono le fatture che ha ricevuto in un anno, 196 file. Le avete anche voi. Quando le avete guardate tutte insieme l'ultima volta?" |
| 0:45–1:15 | Trascinamento, tre caselle che si accendono | "Gliele do tutte e gli chiedo: dove vanno i miei soldi, e cosa non torna?" |
| 1:15–3:00 | Le tre schede, la cifra a destra che sale | Leggere una scoperta alla volta. Fermarsi sulla fattura doppia e sul macchinario restituito: "L'hanno ritirata a giugno. Il canone no." Aprire una volta "Come l'ho calcolato". |
| 3:00–3:20 | Cifra finale 2.733,66 € | "Quasi due mesi di affitto. Erano già nei suoi file." |
| 3:20–5:30 | Domande dalla sala, scritte a mano | "Adesso chiedete voi. Qualsiasi cosa su queste fatture." Due o tre domande. Ripetere la domanda ad alta voce mentre la si scrive. |
| 5:30–6:00 | Scheda dell'ultima risposta | "L'ha fatto in venti secondi, su tutto, e senza che glielo chiedessi riga per riga. Questo vuol dire meno costi." |

### Se una risposta va storta

- **Cifra che non convince.** Aprire "Come l'ho calcolato" e leggere con la sala le fatture usate. Se ha capito male la domanda, riformularla.
- **Domanda fuori dai dati.** "Qui ci sono solo gli acquisti. Con le fatture emesse potrebbe dirvelo."
- **Lentezza o errore.** Passare alla domanda successiva; dopo due errori di fila, chiudere con la cifra a destra, che resta vera.
- **Domanda tecnica di mestiere.** Prodotti e prezzi sono inventati: dirlo subito.
