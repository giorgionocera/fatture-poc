// La pagina: caricamento per trascinamento, prima analisi, conversazione, cifra trovata.
(function () {
  const $ = s => document.querySelector(s);
  const MESI = ["gennaio", "febbraio", "marzo", "aprile", "maggio", "giugno", "luglio", "agosto", "settembre", "ottobre", "novembre", "dicembre"];
  const attesa = ms => new Promise(ok => setTimeout(ok, ms));
  let stato = null, occupato = false, replay = false, trovato = 0;

  const euro = v => formatoNumero(v, 2) + " €";
  const giorno = iso => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(2, 4)}`;
  const giornoLungo = iso => `${iso.slice(8, 10)}/${iso.slice(5, 7)}/${iso.slice(0, 4)}`;
  const meseAnno = iso => `${MESI[+iso.slice(5, 7) - 1]} ${iso.slice(0, 4)}`;
  const breve = nome => (nome || "").replace(/\s+(S\.r\.l\.|S\.p\.A\.|S\.n\.c\.|S\.a\.s\.|Soc\. Coop\.)$/, "");

  function crea(tag, classe, testo) {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (testo != null) e.textContent = testo;
    return e;
  }

  // ── La pagina è disegnata per 1920×1080 e si adatta alla finestra ──
  function scala() {
    const k = Math.min(innerWidth / 1920, innerHeight / 1080);
    $("#palco").style.transform = `translate(-50%, -50%) scale(${k})`;
  }
  addEventListener("resize", scala);
  scala();

  function conta(elemento, da, a, formato, durata = 900) {
    const inizio = performance.now();
    return new Promise(fine => {
      (function passo(ora) {
        const t = Math.min(1, (ora - inizio) / durata), morbido = 1 - Math.pow(1 - t, 3);
        elemento.textContent = formato(da + (a - da) * morbido);
        t < 1 ? requestAnimationFrame(passo) : fine();
      })(inizio);
    });
  }

  // ── Sinistra ──
  function disegnaFatture(animato) {
    const n = stato.statistiche;
    $("#trascina").hidden = true;
    $("#caricate").hidden = false;
    $("#periodo").textContent = `${meseAnno(n.periodo[0])} – ${meseAnno(n.periodo[1])}`;
    $("#fornitori").textContent = n.fornitori;
    const elenco = $("#elenco");
    elenco.replaceChildren(...stato.fatture.map(f => {
      const riga = crea("a", "fattura");   // un clic apre la fattura in un'altra scheda, in forma leggibile
      riga.href = "/fattura/" + encodeURIComponent(f.file);
      riga.target = "_blank";
      riga.dataset.file = f.file;
      riga.dataset.cerca = semplice(`${f.fornitore} ${f.numero}`);
      riga.dataset.doppione = f.doppione ? 1 : 0;
      riga.dataset.importo = f.doppione ? 0 : f.imponibile;   // la fattura doppia non entra nella somma, come nelle risposte
      riga.title = `Apri la fattura ${f.numero}`;
      riga.append(crea("span", "giorno", giorno(f.data)), crea("span", "chi", breve(f.fornitore)), crea("span", "quanto", euro(f.imponibile)));
      return riga;
    }));
    filtra();
    const intero = v => Math.round(v).toString();
    return animato ? conta($("#conta-file"), 0, n.file, intero, 1500) : ($("#conta-file").textContent = n.file);
  }

  // Ricerca per fornitore (o numero di fattura): filtra l'elenco e mostra quante fatture e quanto valgono,
  // per confrontarle con le cifre delle risposte. Senza maiuscole né accenti.
  const semplice = t => (t || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
  function filtra() {
    const parole = semplice($("#cerca").value).split(/\s+/).filter(Boolean);
    let quante = 0, somma = 0, doppie = 0;
    for (const riga of document.querySelectorAll("#elenco .fattura")) {
      const dentro = parole.every(p => riga.dataset.cerca.includes(p));
      riga.hidden = !dentro;
      if (dentro) { quante++; somma += +riga.dataset.importo; doppie += +riga.dataset.doppione; }
    }
    $("#cerca-svuota").hidden = !parole.length;
    const esito = $("#cerca-esito");
    esito.hidden = !parole.length;
    if (parole.length) {
      esito.replaceChildren(
        crea("span", "quante", (quante === 0 ? "nessuna fattura" : quante === 1 ? "1 fattura" : `${quante} fatture`) + (doppie ? " · 1 doppia" : "")),
        crea("span", "somma", quante ? euro(Math.round(somma * 100) / 100) : ""));
      $("#elenco").scrollTop = 0;
    }
  }
  $("#cerca").addEventListener("input", filtra);
  $("#cerca").addEventListener("keydown", e => { if (e.key === "Escape") { $("#cerca").value = ""; filtra(); } });
  $("#cerca-svuota").addEventListener("click", () => { $("#cerca").value = ""; filtra(); $("#cerca").focus(); });

  function segnaDoppie(file) {
    for (const nome of file || []) {
      const riga = document.querySelector(`.fattura[data-file="${nome}"]`);
      if (riga) riga.classList.add("doppia");
    }
  }

  // ── Destra ──
  async function aggiungiVoce(v, animato) {
    const riga = crea("div", "voce");
    riga.append(crea("span", "titolo", v.titolo), crea("span", "importo", euro(v.importo)), crea("span", "dettaglio", breve(v.dettaglio)));
    $("#voci").append(riga);
    const prima = trovato;
    trovato = Math.round((trovato + v.importo) * 100) / 100;
    if (animato) await conta($("#trovato-cifra"), prima, trovato, euro);
    else $("#trovato-cifra").textContent = euro(trovato);
  }

  function mostraFuturo(voci) {
    if (!voci || !voci.length) return;
    $("#futuro-voci").replaceChildren(...voci.map(v => {
      const riga = crea("div", "voce");
      riga.append(crea("span", "titolo", v.titolo.split(" – ")[0]), crea("span", "importo", euro(v.importo_annuo)), crea("span", "dettaglio", v.dettaglio));
      return riga;
    }));
    $("#futuro").hidden = false;
  }

  // ── Schede ──
  function tabellaFatture(fatture) {
    const scatola = crea("div", "tabella-fatture"), t = crea("table"), testa = crea("tr");
    for (const [nome, cls] of [["Fornitore", ""], ["Fattura", ""], ["Data", ""], ["Importo", "num"]]) testa.append(crea("th", cls, nome));
    const thead = crea("thead"); thead.append(testa);
    const corpo = crea("tbody");
    for (const f of fatture) {
      const r = crea("tr");
      const numero = crea("td");
      if (f.file) {
        const apri = crea("a", "apri-fattura", f.numero);
        apri.href = "/fattura/" + encodeURIComponent(f.file); apri.target = "_blank"; apri.title = "Apri la fattura";
        numero.append(apri);
      } else numero.textContent = f.numero;
      r.append(crea("td", "", breve(f.fornitore)), numero, crea("td", "", giornoLungo(f.data)), crea("td", "num", euro(f.importo)));
      corpo.append(r);
    }
    t.append(thead, corpo); scatola.append(t);
    return scatola;
  }

  function tabellaDati(tabella) {
    const scatola = crea("div", "tabella-fatture"), t = crea("table"), testa = crea("tr");
    for (const c of tabella.colonne) testa.append(crea("th", "", c.replaceAll("_", " ")));
    const thead = crea("thead"); thead.append(testa);
    const corpo = crea("tbody");
    for (const riga of tabella.righe) {
      const r = crea("tr");
      for (const v of riga) r.append(crea("td", typeof v === "number" ? "num" : "", typeof v === "number" ? formatoNumero(v) : (v ?? "")));
      corpo.append(r);
    }
    t.append(thead, corpo); scatola.append(t);
    return scatola;
  }

  function comeCalcolato(testo, fatture, interrogazioni) {
    const d = crea("details", "come"), s = crea("summary", "", "Come l'ho calcolato");
    d.append(s);
    let frase = testo || "";
    if (fatture && fatture.length) {
      const tutte = stato.statistiche && fatture.length >= stato.statistiche.fatture_valide;
      frase += (frase ? " " : "") + (tutte ? `Ho letto tutte le ${fatture.length} fatture.` : fatture.length === 1 ? "Viene da questa fattura:" : `Viene da queste ${fatture.length} fatture:`);
    }
    if (frase) d.append(crea("p", "come-testo", frase));
    if (fatture && fatture.length) d.append(tabellaFatture(fatture));
    if (interrogazioni && interrogazioni.length) {
      const tecnici = crea("details", "tecnici");
      tecnici.append(crea("summary", "", "Dettagli tecnici"));
      for (const q of interrogazioni) tecnici.append(crea("pre", "", q));
      d.append(tecnici);
    }
    d.addEventListener("toggle", () => inVista(d.closest(".scheda")));
    return d;
  }

  function schedaScoperta(s) {
    const a = crea("article", "scheda scoperta");
    a.append(crea("div", "etichetta", `[ ${s.numero} ] ${s.titolo}`));
    const corpo = crea("div", "scheda-corpo" + (s.grafico ? " con-grafico" : ""));
    const sinistra = crea("div");
    sinistra.append(crea("div", "cifra", s.cifra), crea("div", "sotto-cifra", s.sotto_cifra), crea("p", "frase", s.frase));
    corpo.append(sinistra);
    if (s.grafico) corpo.append(disegnaGrafico(s.grafico));
    a.append(corpo);
    if (s.voci && s.voci.length) {
      const voci = crea("div", "voci-scheda");
      for (const v of s.voci) {
        const riga = crea("div", "voce-scheda");
        riga.append(crea("span", "nome", v.nome), crea("span", "valore", v.valore), crea("span", "nota", v.nota));
        voci.append(riga);
      }
      a.append(voci);
    }
    a.append(comeCalcolato(s.come.testo, s.come.fatture, null));
    return a;
  }

  function passiInParole(passi) {
    const daTacere = ["Preparo il grafico", "Ricontrollo le cifre", "Sto ripassando come sono fatte le fatture"];
    const pezzi = (passi || []).filter(p => !daTacere.includes(p))
      .map(p => p === "Riguardo quello che avevo già trovato" ? "quello che avevo trovato nella prima analisi" : p.replace(/^Sto guardando /, "").replace(/^Sto /, ""));
    if (!pezzi.length) return "";
    return "Ho guardato " + pezzi.map(p => p[0].toLowerCase() + p.slice(1)).join("; poi ") + ".";
  }

  function schedaRisposta(s) {
    const a = crea("article", "scheda risposta" + (s.esito === "ok" ? "" : " tenue"));
    a.append(crea("div", "etichetta", "[ Domanda ]"), crea("h3", "", s.domanda));
    if (s.cifra) a.append(crea("div", "cifra", s.cifra));
    a.append(crea("p", "frase", s.testo));
    if (s.tabella) a.append(tabellaDati(s.tabella));
    if (s.grafico) a.append(disegnaGrafico(s.grafico));
    const haCome = (s.come && ((s.come.fatture && s.come.fatture.length) || (s.come.passi && s.come.passi.length))) || (s.interrogazioni && s.interrogazioni.length);
    if (haCome && s.esito !== "errore") a.append(comeCalcolato(passiInParole(s.come.passi), s.come.fatture, s.interrogazioni));
    return a;
  }

  // Porta in vista l'ultima scheda: se ci sta tutta la si vede intera, altrimenti si parte dalla sua cima.
  function inVista(scheda) {
    const c = $("#conversazione");
    requestAnimationFrame(() => {
      const cima = scheda.offsetTop - c.offsetTop;
      const fondo = cima + scheda.offsetHeight - c.clientHeight;
      c.scrollTo({ top: scheda.offsetHeight > c.clientHeight ? cima : Math.max(0, fondo), behavior: "smooth" });
    });
  }

  // ── Caricamento e prima analisi ──
  function casella(n, classe, riga) {
    const c = document.querySelector(`.casella[data-n="${n}"]`);
    c.classList.remove("attiva", "fatta");
    if (classe) c.classList.add(classe);
    if (riga != null) c.querySelector(".casella-riga").textContent = riga;
  }

  async function leggiCartella(voci) {
    const file = [];
    async function visita(voce) {
      if (voce.isFile) {
        if (/\.xml$/i.test(voce.name)) file.push(await new Promise((ok, ko) => voce.file(ok, ko)));
      } else if (voce.isDirectory) {
        const lettore = voce.createReader();
        for (;;) {
          const lotto = await new Promise((ok, ko) => lettore.readEntries(ok, ko));
          if (!lotto.length) break;
          for (const v of lotto) await visita(v);
        }
      }
    }
    for (const v of voci) await visita(v);
    return file;
  }

  function erroreCaricamento(testo) {
    $("#trascina").hidden = false;
    $("#caricate").hidden = true;
    $("#trascina").classList.add("errore");
    $("#trascina-nota").textContent = testo;
    $("#caselle").hidden = true;
    $("#benvenuto").hidden = false;
  }

  async function carica(file) {
    if (occupato) return;
    if (!file.length) return erroreCaricamento("In questa cartella non ci sono fatture elettroniche.");
    occupato = true;
    const minimo = (stato.pagina.secondi_per_casella ?? 1.8) * 1000;
    try {
      $("#benvenuto").hidden = true;
      $("#conversazione").replaceChildren();
      $("#cerca").value = "";
      $("#voci").replaceChildren(); $("#futuro").hidden = true;
      trovato = 0; $("#trovato-cifra").textContent = euro(0);
      $("#caselle").hidden = false; $("#caselle").classList.remove("compatte");
      [1, 2, 3].forEach(n => casella(n, "", ""));

      casella(1, "attiva");
      const corpo = { file: await Promise.all(file.map(async f => ({ nome: f.name, testo: await f.text() }))) };
      const [risposta] = await Promise.all([fetch("/api/carica", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(corpo) }), attesa(300)]);
      const dati = await risposta.json();
      if (!risposta.ok) throw new Error(dati.errore || "Caricamento non riuscito.");
      stato.statistiche = dati.statistiche; stato.fatture = dati.fatture; stato.caricato = true;
      stato.generazione = (await (await fetch("/api/stato")).json()).generazione;
      const n = dati.statistiche;
      await Promise.all([disegnaFatture(true), attesa(minimo)]);
      casella(1, "fatta", `${n.file} file, da ${meseAnno(n.periodo[0])} a ${meseAnno(n.periodo[1])}.`);

      casella(2, "attiva");
      await attesa(minimo);
      casella(2, "fatta", `${n.fornitori} fornitori, ${n.righe} righe, ${n.categorie} voci di spesa.`);

      casella(3, "attiva");
      const [r2] = await Promise.all([fetch("/api/analisi", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ replay }) }), attesa(minimo)]);
      const analisi = await r2.json();
      if (!r2.ok) throw new Error(analisi.errore || "Analisi non riuscita.");
      stato.analisi = analisi;
      casella(3, "fatta", analisi.cose_trovate === 1 ? "Ho trovato 1 cosa da guardare." : `Ho trovato ${analisi.cose_trovate} cose da guardare.`);
      await attesa(900);
      $("#caselle").classList.add("compatte");
      await mostraAnalisi(analisi, true);
    } catch (e) {
      erroreCaricamento(e.message);
    } finally {
      occupato = false;
      $("#domanda").focus();
    }
  }

  // Tra una scoperta e l'altra decide chi presenta: freccia destra, spazio o invio a campo vuoto (o un clic su "avanti").
  // Con secondi_tra_scoperte > 0 in config.toml si va avanti da soli dopo quella pausa.
  let avanti = null;
  function aspettaAvanti() {
    const secondi = stato.pagina.secondi_tra_scoperte ?? 0;
    if (secondi > 0) return attesa(secondi * 1000);
    $("#avanti").hidden = false;
    const ultima = $("#conversazione").lastElementChild;
    if (ultima) inVista(ultima);
    return new Promise(ok => { avanti = () => { avanti = null; $("#avanti").hidden = true; ok(); }; });
  }
  $("#avanti").addEventListener("click", () => avanti && avanti());

  async function mostraAnalisi(analisi, animato) {
    for (const [i, s] of analisi.scoperte.entries()) {
      const scheda = schedaScoperta(s);
      $("#conversazione").append(scheda);
      if (animato) inVista(scheda);
      for (const v of s.aggiunge) {
        if (animato) await attesa(500);
        await aggiungiVoce(v, animato);
      }
      if (s.id === "non_torna") segnaDoppie(analisi.doppioni);
      if (animato && i < analisi.scoperte.length - 1) await aspettaAvanti();
    }
    mostraFuturo(analisi.trovato.futuro);
  }

  // ── Domande libere ──
  async function chiedi(testo) {
    if (occupato) return;
    occupato = true;
    $("#chiedi").classList.add("occupato");
    $("#benvenuto").hidden = true;
    const provvisoria = crea("article", "scheda risposta al-lavoro");
    const frase = crea("p", "frase", stato.caricato ? "Ci penso" : "");
    provvisoria.append(crea("div", "etichetta", "[ Domanda ]"), crea("h3", "", testo), frase);
    $("#conversazione").append(provvisoria);
    inVista(provvisoria);
    let scheda = null;
    try {
      const r = await fetch("/api/domanda", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ testo }) });
      if (!r.ok) {
        scheda = { domanda: testo, esito: "errore", testo: (await r.json()).errore || "Qualcosa è andato storto." };
      } else {
        const lettore = r.body.getReader(), decodifica = new TextDecoder();
        let resto = "";
        for (;;) {
          const { done, value } = await lettore.read();
          if (done) break;
          resto += decodifica.decode(value, { stream: true });
          const righe = resto.split("\n");
          resto = righe.pop();
          for (const riga of righe.filter(Boolean)) {
            const evento = JSON.parse(riga);
            if (evento.tipo === "passo") frase.textContent = evento.testo;
            if (evento.tipo === "scheda") scheda = evento.scheda;
          }
        }
      }
    } catch (e) {
      scheda = null;
    }
    scheda = scheda || { domanda: testo, esito: "errore", testo: "Non riesco a raggiungere l'applicazione. Riprova." };
    const finale = schedaRisposta(scheda);
    provvisoria.replaceWith(finale);
    inVista(finale);
    occupato = false;
    $("#chiedi").classList.remove("occupato");
    $("#domanda").focus();
  }

  $("#chiedi").addEventListener("submit", e => {
    e.preventDefault();
    const testo = $("#domanda").value.trim();
    if (!testo || occupato) return;
    $("#domanda").value = "";
    chiedi(testo);
  });

  // ── Trascinamento ──
  let dentro = 0;
  addEventListener("dragenter", e => { e.preventDefault(); dentro++; document.body.classList.add("sopra"); });
  addEventListener("dragleave", () => { if (--dentro <= 0) { dentro = 0; document.body.classList.remove("sopra"); } });
  addEventListener("dragover", e => e.preventDefault());
  addEventListener("drop", async e => {
    e.preventDefault();
    dentro = 0; document.body.classList.remove("sopra");
    const voci = [...e.dataTransfer.items].map(i => i.webkitGetAsEntry && i.webkitGetAsEntry()).filter(Boolean);
    carica(voci.length ? await leggiCartella(voci) : [...e.dataTransfer.files].filter(f => /\.xml$/i.test(f.name)));
  });
  $("#trascina").addEventListener("click", () => $("#scegli-cartella").click());
  $("#trascina").addEventListener("keydown", e => { if (e.key === "Enter" || e.key === " ") $("#scegli-cartella").click(); });
  $("#scegli-cartella").addEventListener("change", e => carica([...e.target.files].filter(f => /\.xml$/i.test(f.name))));

  // ── Tastiera: Opzione+R attiva il replay della prima analisi ──
  addEventListener("keydown", e => {
    if (avanti && !e.altKey && !e.metaKey && document.activeElement !== $("#cerca") && (e.key === "ArrowRight" || ((e.key === " " || e.key === "Enter") && !$("#domanda").value))) {
      e.preventDefault();
      return avanti();
    }
    if (e.altKey && e.code === "KeyR") {
      e.preventDefault();
      replay = !replay;
      $("#spia-replay").hidden = !replay;
    }
  });

  // ── Avvio: ridisegna tutto dallo stato, così un ricaricamento della pagina non perde nulla ──
  async function avvio() {
    stato = await (await fetch("/api/stato")).json();
    const imp = stato.impresa, tema = imp.tema || {};
    if (tema.accento) document.documentElement.style.setProperty("--accento", tema.accento);
    if (tema.evidenza) document.documentElement.style.setProperty("--evidenza", tema.evidenza);
    $("#sigla").textContent = imp.sigla || "";
    $("#nome-impresa").textContent = imp.nome;
    $("#attivita").textContent = imp.attivita || "";
    $("#dicitura").textContent = imp.dicitura || "";
    $("#domanda").placeholder = stato.pagina.suggerimento || "";
    document.title = `Le fatture che parlano · ${imp.nome}`;
    if (stato.caricato) {
      $("#benvenuto").hidden = true;
      disegnaFatture(false);
      if (stato.analisi) {
        const n = stato.statistiche;
        $("#caselle").hidden = false; $("#caselle").classList.add("compatte");
        casella(1, "fatta", `${n.file} file, da ${meseAnno(n.periodo[0])} a ${meseAnno(n.periodo[1])}.`);
        casella(2, "fatta", `${n.fornitori} fornitori, ${n.righe} righe, ${n.categorie} voci di spesa.`);
        casella(3, "fatta", `Ho trovato ${stato.analisi.cose_trovate} cose da guardare.`);
        await mostraAnalisi(stato.analisi, false);
      }
      for (const s of stato.schede) $("#conversazione").append(schedaRisposta(s));
      const ultima = $("#conversazione").lastElementChild;
      if (ultima && stato.schede.length) inVista(ultima);
    }
    // se l'applicazione viene riportata allo stato iniziale (./demo reset) o aggiornata, la pagina si ricarica da sola
    setInterval(async () => {
      if (occupato) return;
      try {
        const nuovo = await (await fetch("/api/stato")).json();
        if (nuovo.generazione !== stato.generazione || nuovo.versione !== stato.versione) location.reload();
      } catch (e) { /* server spento: si riprova al prossimo giro */ }
    }, 2500);
  }
  avvio();
})();
