// Grafici disegnati dall'app, senza librerie esterne: barre orizzontali e linea.
// Una sola serie, quindi un solo colore (l'accento) e nessuna legenda: il titolo dice cosa si guarda.
(function () {
  const MESI = ["gen", "feb", "mar", "apr", "mag", "giu", "lug", "ago", "set", "ott", "nov", "dic"];
  const SVG = "http://www.w3.org/2000/svg";

  // Formato italiano scritto a mano: toLocaleString("it-IT") non mette il punto nei numeri di quattro cifre (2733,66).
  function numero(v, decimali) {
    const d = decimali ?? (Number.isInteger(v) ? 0 : 2);
    const [intero, dec] = Math.abs(v).toFixed(d).split(".");
    return (v < 0 ? "-" : "") + intero.replace(/\B(?=(\d{3})+(?!\d))/g, ".") + (dec ? "," + dec : "");
  }
  window.formatoNumero = numero;

  function etichetta(testo) {
    const m = /^(\d{4})-(\d{2})(?:-(\d{2}))?$/.exec(testo);
    if (!m) return testo;
    return m[3] ? `${m[3]}/${m[2]}/${m[1].slice(2)}` : `${MESI[+m[2] - 1]} ${m[1].slice(2)}`;
  }

  function crea(tag, classe, testo) {
    const e = document.createElement(tag);
    if (classe) e.className = classe;
    if (testo != null) e.textContent = testo;
    return e;
  }

  function svg(tag, attributi) {
    const e = document.createElementNS(SVG, tag);
    for (const [k, v] of Object.entries(attributi || {})) e.setAttribute(k, v);
    return e;
  }

  const fumetto = () => document.getElementById("fumetto");
  function mostraFumetto(testo, x, y) {
    const f = fumetto();
    f.textContent = testo;
    f.style.left = x + "px";
    f.style.top = y + "px";
    f.hidden = false;
  }
  function nascondiFumetto() { fumetto().hidden = true; }

  function barre(contenitore, g) {
    const massimo = Math.max(...g.punti.map(p => Math.abs(p.valore)), 1e-9);
    const decimali = g.punti.every(p => Number.isInteger(p.valore)) ? 0 : 2;
    const griglia = crea("div", "barre");
    for (const p of g.punti) {
      const riga = crea("div", "riga");
      const nome = crea("div", "nome", etichetta(p.etichetta));
      const pista = crea("div", "pista");
      const barra = crea("div", "barra");
      barra.style.width = "0%";
      pista.append(barra);
      const valore = crea("div", "valore", numero(p.valore, decimali) + (g.unita ? " " + g.unita : ""));
      if (p.nota) valore.append(crea("small", "", p.nota));
      riga.append(nome, pista, valore);
      riga.addEventListener("mousemove", e => mostraFumetto(`${etichetta(p.etichetta)}: ${valore.textContent}`, e.clientX, e.clientY));
      riga.addEventListener("mouseleave", nascondiFumetto);
      griglia.append(riga);
      requestAnimationFrame(() => requestAnimationFrame(() => { barra.style.width = (100 * Math.abs(p.valore) / massimo) + "%"; }));
    }
    contenitore.append(griglia);
  }

  function linea(contenitore, g) {
    const L = 1000, A = 330, sx = 96, dx = 40, su = 40, giu = 44;
    const valori = g.punti.map(p => p.valore);
    let minimo = Math.min(...valori), massimo = Math.max(...valori);
    if (minimo === massimo) { minimo -= 1; massimo += 1; }
    // tacche tonde: 4.000 · 5.500 · 7.000 invece di 4.178 · 5.590 · 7.002
    const grezzo = (massimo - minimo) / 2, potenza = Math.pow(10, Math.floor(Math.log10(grezzo)));
    const passoY = [1, 2, 2.5, 5, 10].map(m => m * potenza).find(m => m >= grezzo * 0.75);
    let basso = Math.floor(minimo / passoY) * passoY;
    if (minimo >= 0 && basso < 0) basso = 0;
    const tacche = Math.max(2, Math.ceil((massimo - basso) / passoY - 1e-9));
    const alto = basso + tacche * passoY;
    const x = i => sx + (L - sx - dx) * (g.punti.length === 1 ? 0.5 : i / (g.punti.length - 1));
    const y = v => su + (A - su - giu) * (1 - (v - basso) / (alto - basso));
    const decimali = passoY < 1 ? 2 : 0;

    const s = svg("svg", { viewBox: `0 0 ${L} ${A}`, role: "img", "aria-label": g.titolo || "Andamento" });
    for (let k = 0; k <= tacche; k++) {
      const v = basso + passoY * k;
      s.append(svg("line", { class: "griglia", x1: sx, x2: L - dx, y1: y(v), y2: y(v) }));
      const t = svg("text", { class: "asse", x: sx - 12, y: y(v) + 7, "text-anchor": "end" });
      t.textContent = numero(v, decimali);
      s.append(t);
    }
    const passo = Math.ceil(g.punti.length / 6);
    const ultimo = g.punti.length - 1;
    g.punti.forEach((p, i) => {
      if (i !== ultimo && (i % passo || ultimo - i < passo)) return;   // l'ultima etichetta c'è sempre, senza vicine addosso
      const t = svg("text", { class: "asse", x: x(i), y: A - 10, "text-anchor": "middle" });
      t.textContent = etichetta(p.etichetta);
      s.append(t);
    });
    s.append(svg("polyline", { class: "tratto", points: g.punti.map((p, i) => `${x(i)},${y(p.valore)}`).join(" ") }));
    const mirino = svg("line", { class: "mirino", y1: su - 10, y2: A - giu, visibility: "hidden" });
    s.append(mirino);
    const cerchi = g.punti.map((p, i) => {
      const c = svg("circle", { class: "punto", cx: x(i), cy: y(p.valore), r: 6 });
      s.append(c);
      return c;
    });
    // etichette dirette solo sul punto più alto e sull'ultimo: il resto si legge passando sopra
    const iMax = valori.indexOf(massimo);
    for (const i of new Set([iMax, g.punti.length - 1])) {
      const ancora = i === 0 ? "start" : i === g.punti.length - 1 ? "end" : "middle";
      const sotto = i !== iMax && i > 0 && valori[i - 1] > valori[i];   // se la linea scende verso il punto, l'etichetta va sotto
      const t = svg("text", { class: "valore-punto", x: x(i), y: y(valori[i]) + (sotto ? 30 : -16), "text-anchor": ancora });
      t.textContent = numero(valori[i]);
      s.append(t);
    }
    s.addEventListener("mousemove", e => {
      const r = s.getBoundingClientRect();
      const px = (e.clientX - r.left) / r.width * L;
      let i = 0;
      g.punti.forEach((_, k) => { if (Math.abs(x(k) - px) < Math.abs(x(i) - px)) i = k; });
      cerchi.forEach((c, k) => c.classList.toggle("vicino", k === i));
      mirino.setAttribute("x1", x(i)); mirino.setAttribute("x2", x(i)); mirino.setAttribute("visibility", "visible");
      mostraFumetto(`${etichetta(g.punti[i].etichetta)}: ${numero(valori[i])}`, r.left + x(i) / L * r.width, r.top + y(valori[i]) / A * r.height);
    });
    s.addEventListener("mouseleave", () => {
      cerchi.forEach(c => c.classList.remove("vicino"));
      mirino.setAttribute("visibility", "hidden");
      nascondiFumetto();
    });
    contenitore.append(s);
  }

  // Torta (ad anello): come si divide un totale, al massimo sei fette, dalla più grande, in senso orario da mezzogiorno.
  // Colori categorici in ordine fisso, controllati per chi distingue male i colori; «Altre» in grigio.
  // Accanto, l'elenco con nome, valore e percentuale: la fetta non si legge mai dal solo colore.
  const COLORI_TORTA = ["#257de0", "#f47230", "#00b894", "#f2a600", "#ee7fac", "#008a17"];
  const GRIGIO_ALTRE = "#8C857C";

  function torta(contenitore, g) {
    const totale = g.punti.reduce((t, p) => t + p.valore, 0);
    const decimali = g.punti.every(p => Number.isInteger(p.valore)) ? 0 : 2;
    const quota = v => numero(100 * v / totale, 1) + "%";
    const L = 300, c = L / 2, R = 142, r = 82;
    const scatola = crea("div", "torta-corpo");
    const s = svg("svg", { viewBox: `0 0 ${L} ${L}`, width: L, height: L, role: "img", "aria-label": g.titolo || "Come si divide il totale" });
    const elenco = crea("div", "torta-elenco");
    const pezzi = [];
    let inizio = -Math.PI / 2;
    const punto = (raggio, angolo) => `${c + raggio * Math.cos(angolo)},${c + raggio * Math.sin(angolo)}`;
    g.punti.forEach((p, i) => {
      const colore = p.altre ? GRIGIO_ALTRE : COLORI_TORTA[i % COLORI_TORTA.length];
      const ampiezza = 2 * Math.PI * p.valore / totale, fine = inizio + ampiezza, grande = ampiezza > Math.PI ? 1 : 0;
      const fetta = svg("path", { class: "fetta", fill: colore,
        d: `M${punto(R, inizio)} A${R},${R} 0 ${grande} 1 ${punto(R, fine)} L${punto(r, fine)} A${r},${r} 0 ${grande} 0 ${punto(r, inizio)} Z` });
      s.append(fetta);
      inizio = fine;
      const riga = crea("div", "torta-riga");
      const campione = crea("span", "campione"); campione.style.background = colore;
      riga.append(campione, crea("span", "nome", etichetta(p.etichetta)), crea("span", "valore", numero(p.valore, decimali)), crea("span", "quota", quota(p.valore)));
      elenco.append(riga);
      const testo = `${etichetta(p.etichetta)}: ${numero(p.valore, decimali)} (${quota(p.valore)})`;
      pezzi.push([fetta, riga]);
      const accendi = (e) => {
        pezzi.forEach(([f, rr], k) => { f.classList.toggle("spenta", k !== i); rr.classList.toggle("accesa", k === i); });
        mostraFumetto(testo, e.clientX, e.clientY);
      };
      const spegni = () => { pezzi.forEach(([f, rr]) => { f.classList.remove("spenta"); rr.classList.remove("accesa"); }); nascondiFumetto(); };
      for (const bersaglio of [fetta, riga]) { bersaglio.addEventListener("mousemove", accendi); bersaglio.addEventListener("mouseleave", spegni); }
    });
    const centro = svg("text", { x: c, y: c + 4, "text-anchor": "middle", class: "torta-totale" });
    centro.textContent = numero(totale, decimali);
    const sotto = svg("text", { x: c, y: c + 32, "text-anchor": "middle", class: "torta-sotto" });
    sotto.textContent = "in tutto";
    s.append(centro, sotto);
    scatola.append(s, elenco);
    contenitore.append(scatola);
  }

  window.disegnaGrafico = function (g) {
    const forma = { linea, torta }[g.tipo] || barre;
    const scatola = crea("div", "grafico " + (g.tipo === "linea" ? "linea" : g.tipo === "torta" ? "torta" : "barre-scatola"));
    if (g.titolo) scatola.append(crea("div", "grafico-titolo", g.titolo));
    forma(scatola, g);
    return scatola;
  };
})();
