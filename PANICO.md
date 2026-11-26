# Demo fatture – se va storto

Aggiornato al 26/11/2026. Da leggere con `cat PANICO.md`.

## Prima di salire (10 minuti prima)

- [ ] Docker Desktop acceso, poi `./demo avvia` e `./demo reset`: pagina vuota su `http://localhost:8002`
- [ ] Finestra del browser a tutto schermo, schermo duplicato sul proiettore
- [ ] Cartella delle fatture (copia di `contesto/dati/fatture`) sul desktop, pronta da trascinare
- [ ] Una domanda di prova a mano ("quanto ho speso in tutto?" → 67.808,52 €), poi `./demo reset`
- [ ] Terminale aperto nella cartella della demo, a portata di mano ma fuori dallo schermo proiettato

## Se va storto

La cifra sul verde a destra viene dalle regole, non dal modello: resta vera anche se tutto il resto si blocca.

| Cosa succede | Cosa fai subito |
| --- | --- |
| Il trascinamento non parte | Clic sul riquadro a sinistra e scegli la cartella |
| La casella 03 resta accesa più di 20 secondi | Aspetta fino a 30: se il modello non risponde, le schede escono lo stesso con le frasi scritte dal codice |
| Vuoi una prima analisi senza rischi | Prima di caricare premi Opzione+R (puntino grigio in alto a destra): ripete l'ultima analisi riuscita senza chiamare il modello |
| Le scoperte non avanzano | Freccia destra, oppure clic su "Prossima scoperta" (se il cursore è nel campo di ricerca, prima clicca fuori) |
| Una cifra non convince | Apri "Come l'ho calcolato" e leggi le fatture con la sala; oppure cerca il fornitore nella colonna di sinistra e confronta la somma |
| L'agente ha capito male la domanda | Riformulala più precisa, ad alta voce mentre la scrivi |
| "Ecco i dati, giudicate voi" | Il controllo ha fermato una cifra non verificata: è la rete di sicurezza, dillo. Passa alla domanda successiva |
| Errore o lentezza su una domanda | Passa alla successiva. Dopo due errori di fila, chiudi con la cifra sul verde |
| Pagina bianca o bloccata | Ricarica la pagina (Cmd+R): ritrovi tutto com'era |
| Ricaricare non basta | `./demo riavvia`, poi ricarica la pagina |
| Vuoi ricominciare da capo | `./demo reset`: la pagina si svuota da sola, ritrascina la cartella |
| Niente internet in sala | Hotspot del telefono. Senza rete: Opzione+R per la prima analisi, niente domande, chiudi con la cifra sul verde |

## Comandi

Tutti dalla cartella della demo.

| Comando | Quando |
| --- | --- |
| `./demo avvia` | Accendere l'app e aprire la pagina |
| `./demo reset` | Tornare alla pagina vuota |
| `./demo riavvia` | La pagina non risponde o hai cambiato `config.toml` |
| `./demo registro` | Vedere cosa ha chiesto e cosa ha risposto l'agente |
| `./demo diario` | Vedere gli errori del server |
| `PROFILO=haiku ./demo avvia` | Sonnet troppo lento: Haiku risponde prima, ma sbaglia di più |

## Cosa dire

- **Domanda fuori dai dati**: "Qui ci sono solo gli acquisti. Con le fatture emesse potrebbe dirvelo."
- **Cifra fermata dal controllo**: "Non era sicuro della cifra, quindi non ve la mostra. Preferisce dirvi 'non lo so' che inventare."
- **Domanda tecnica di mestiere**: "Prodotti e prezzi sono inventati: l'impresa non esiste."
- **Lentezza o errore**: "Sta parlando con un modello in rete, a volte ci mette di più. Intanto la cifra a destra resta: 2.733,66 €, quasi due mesi di affitto."

Numeri da sapere a memoria: 196 file, 67.808,52 € di spesa, 2.733,66 € trovati (fattura doppia 1.331,50, canone dopo il ritiro 1.040,00, aumenti 254,66, gel 107,50).
