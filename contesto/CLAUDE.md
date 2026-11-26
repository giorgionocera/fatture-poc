# contesto/ – pacchetto di riferimento

Materiale consegnato da chi presenta, già validato. **Non modificarlo**: l'applicazione si costruisce fuori da questa cartella e legge da qui dati e numeri attesi. Unica eccezione: rigenerare o adattare i dati su richiesta esplicita, con `strumenti/genera_fatture.py` (seme fisso, sovrascrive la cartella di uscita), riallineando poi `dati/risposte_attese.json`.

| Percorso | Cos'è | Come usarlo |
| --- | --- | --- |
| `LEGGIMI.md` | Compito, decisioni prese, consegne, ordine di lavoro | Da leggere per primo |
| `docs/SPECIFICA.md` | Specifica completa in 10 sezioni | Documento di riferimento: leggi la sezione che serve |
| `docs/slide_46.png` | Una slide dell'intervento | Famiglia grafica: fondo chiaro caldo, etichette monospaziate tra parentesi quadre, titoli grandi, bordi netti. L'app cambia colore d'accento (non il blu-viola) e impianto; il verde lime è riservato alla cifra trovata |
| `dati/fatture/` | 196 XML FatturaPA (FPR12), nome `IT<partita IVA>_<progressivo>.xml` | È la cartella che viene trascinata nell'app |
| `dati/fornitori.csv` | Categoria e regione dei 19 fornitori | Abbinato per partita IVA al caricamento |
| `dati/risposte_attese.json` | Tutti i numeri attesi | Base dei test automatici |
| `dati/domande_di_prova.json` | 25 domande con le `cifre_attese` | Batteria di prova dell'agente |
| `strumenti/carica_fatture.py` | XML → SQLite (tabelle `fatture`, `righe`, viste `*_valide`) | Implementazione di riferimento: si integra o si riscrive, purché dia gli stessi numeri |
| `strumenti/risposte_attese.py` | Calcolo di ogni cifra attesa | Mostra l'interrogazione dietro ogni numero |
| `strumenti/genera_fatture.py` | Generatore delle fatture inventate | Solo per rigenerare i dati |

## Per non sprecare contesto

- **Non leggere gli XML uno per uno.** Hanno tutti la stessa struttura: ne basta uno come esempio (`dati/fatture/IT09999000102_00007.xml` ha dieci righe, smalti compresi). Per guardare dentro i dati, crea la base dati con `carica_fatture.py` e interrogala con `sqlite3`.
- Di `risposte_attese.json` leggi le chiavi che servono (per esempio con `python3 -c` o `jq`), non l'intero file.
- I file con le quattro storie: fattura doppia in `IT09999000117_00001.xml` e `_00002.xml` (Dermovita); pressoterapia in `IT09999000105_*` (TecnoBeauty); aumenti in `IT09999000101_*` (Linea Pelle); gel in `IT09999000102_*` (Nail Point) e `IT09999000103_*` (Beauty Pro).
