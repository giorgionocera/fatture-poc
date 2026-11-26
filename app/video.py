"""Video della demo: caricamento, tre scoperte, una domanda con "Come l'ho calcolato".

Si lancia con ./demo video, a app accesa. Guida un browser senza interfaccia sulla pagina vera, con il
modello vero, prende i fotogrammi con lo screencast di Chromium e li monta con ffmpeg secondo i loro tempi.
Il cursore è disegnato nella pagina (il browser senza interfaccia non ne mostra uno), con un'onda a ogni clic.
Alla fine riporta l'applicazione allo stato iniziale.
"""
import asyncio
import base64
import os
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

from playwright.async_api import async_playwright

INDIRIZZO = os.environ.get("INDIRIZZO_APP", "http://fatture:8002")
FATTURE = Path("/app/contesto/dati/fatture")
USCITA = Path("/app/video")
DOMANDA = os.environ.get("DOMANDA_VIDEO") or "Quanto spendo di caffè?"
LATO = (1920, 1080)

CURSORE = """
(() => {
  const stile = document.createElement("style");
  stile.textContent = `
    #cursore-video { position: fixed; left: 0; top: 0; width: 30px; height: 30px; z-index: 2147483647; pointer-events: none;
                     transform: translate(-3px, -2px); filter: drop-shadow(0 2px 3px rgba(0,0,0,.35)); }
    .onda-video { position: fixed; z-index: 2147483646; pointer-events: none; width: 16px; height: 16px; margin: -8px 0 0 -8px;
                  border-radius: 50%; border: 3px solid #E8452C; animation: onda-video .6s ease-out forwards; }
    @keyframes onda-video { to { transform: scale(4.5); opacity: 0; } }`;
  const cursore = document.createElement("div");
  cursore.id = "cursore-video";
  cursore.innerHTML = '<svg viewBox="0 0 24 24" width="30" height="30"><path d="M3 2 L3 19 L7.5 14.8 L10.6 21.6 L13.6 20.3 L10.6 13.6 L16.8 13.6 Z" fill="#121212" stroke="#fff" stroke-width="1.6" stroke-linejoin="round"/></svg>';
  const monta = () => { document.head.append(stile); document.body.append(cursore); };
  document.readyState === "loading" ? document.addEventListener("DOMContentLoaded", monta) : monta();
  const dove = JSON.parse(sessionStorage.getItem("cursore-video") || "[960,540]");
  const metti = (x, y) => { cursore.style.left = x + "px"; cursore.style.top = y + "px"; sessionStorage.setItem("cursore-video", JSON.stringify([x, y])); };
  metti(...dove);
  addEventListener("mousemove", e => metti(e.clientX, e.clientY), true);
  addEventListener("mousedown", e => {
    const onda = document.createElement("div");
    onda.className = "onda-video";
    onda.style.left = e.clientX + "px"; onda.style.top = e.clientY + "px";
    document.body.append(onda);
    setTimeout(() => onda.remove(), 700);
  }, true);
})();
"""


class Regista:
    """Muove il cursore come una mano: traiettorie morbide, pause prima dei clic."""

    def __init__(self, pagina):
        self.p = pagina
        self.x, self.y = LATO[0] / 2, LATO[1] / 2

    async def vai(self, x, y, secondi=0.7):
        passi = max(8, int(secondi * 60))
        x0, y0 = self.x, self.y
        for i in range(1, passi + 1):
            t = i / passi
            m = t * t * (3 - 2 * t)  # parte e arriva piano
            await self.p.mouse.move(x0 + (x - x0) * m, y0 + (y - y0) * m)
            await asyncio.sleep(secondi / passi)
        self.x, self.y = x, y

    async def su(self, selettore, secondi=0.7, dx=0.5, dy=0.5):
        scatola = await self.p.locator(selettore).first.bounding_box()
        await self.vai(scatola["x"] + scatola["width"] * dx, scatola["y"] + scatola["height"] * dy, secondi)

    async def clic(self, selettore, secondi=0.7, dx=0.5, dy=0.5):
        await self.su(selettore, secondi, dx, dy)
        await asyncio.sleep(0.25)
        await self.p.mouse.down()
        await asyncio.sleep(0.08)
        await self.p.mouse.up()
        await asyncio.sleep(0.2)


async def registra(cartella_fotogrammi: Path) -> list[tuple[Path, float]]:
    fotogrammi: list[tuple[Path, float]] = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(executable_path="/usr/bin/chromium", args=["--no-sandbox", "--hide-scrollbars"])
        contesto = await browser.new_context(viewport={"width": LATO[0], "height": LATO[1]}, device_scale_factor=1)
        await contesto.add_init_script(CURSORE)
        pagina = await contesto.new_page()
        errori = []
        pagina.on("pageerror", lambda e: errori.append(str(e)))
        await pagina.goto(INDIRIZZO)
        await pagina.wait_for_load_state("networkidle")
        await pagina.wait_for_timeout(800)

        cdp = await contesto.new_cdp_session(pagina)

        def fotogramma(evento):
            numero = len(fotogrammi)
            file = cartella_fotogrammi / f"{numero:06d}.jpg"
            file.write_bytes(base64.b64decode(evento["data"]))
            fotogrammi.append((file, evento["metadata"]["timestamp"]))
            asyncio.ensure_future(cdp.send("Page.screencastFrameAck", {"sessionId": evento["sessionId"]}))

        cdp.on("Page.screencastFrame", fotogramma)
        await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": LATO[0], "maxHeight": LATO[1]})
        r = Regista(pagina)
        await pagina.mouse.move(r.x, r.y)
        inizio = time.monotonic()
        tappa = lambda nome: print(f"  {time.monotonic() - inizio:5.1f}s  {nome}", flush=True)

        tappa("pagina vuota")
        await asyncio.sleep(2.0)
        await r.su(".trascina-testo", 1.2)
        await asyncio.sleep(0.6)
        await r.clic(".trascina-testo", 0.3)
        # il riquadro apre la scelta della cartella: qui la cartella la passa il browser di prova
        await pagina.set_input_files("#scegli-cartella", str(FATTURE))
        tappa("caricamento")
        await r.vai(1240, 640, 1.4)

        await pagina.wait_for_selector(".scoperta", timeout=90000)
        tappa("prima scoperta")
        await asyncio.sleep(5.0)
        for numero in (2, 3):
            await pagina.wait_for_selector("#avanti:not([hidden])", timeout=30000)
            await r.clic("#avanti", 0.9)
            tappa(f"scoperta {numero}")
            await asyncio.sleep(5.5 if numero == 2 else 2.0)
        await pagina.wait_for_selector("#futuro:not([hidden])", timeout=30000)
        await r.vai(1680, 230, 1.0)  # la cifra sul verde
        tappa("cifra finale")
        await asyncio.sleep(3.5)

        await r.clic("#domanda", 1.0, dx=0.3)
        tappa("domanda")
        await pagina.keyboard.type(DOMANDA, delay=85)
        await asyncio.sleep(0.6)
        await r.clic(".chiedi button", 0.6)
        await r.vai(1100, 560, 1.0)
        await pagina.wait_for_function("!document.querySelector('.al-lavoro')", timeout=60000)
        tappa("risposta")
        await asyncio.sleep(4.5)
        await r.clic(".risposta:last-of-type details.come > summary", 0.9, dx=0.12)
        tappa("come l'ho calcolato")
        await asyncio.sleep(1.2)
        await r.vai(1150, 820, 1.2)
        await asyncio.sleep(5.0)

        await cdp.send("Page.stopScreencast")
        await asyncio.sleep(0.3)
        testo = await pagina.locator(".risposta").last.locator(".frase").inner_text()
        print(f"  risposta: {testo}")
        if errori:
            print("  errori nella pagina:", errori)
        await browser.close()
    return fotogrammi


def monta(fotogrammi: list[tuple[Path, float]], cartella: Path, uscita: Path):
    """Ogni fotogramma resta a schermo fino al successivo: i tempi sono quelli veri."""
    elenco = cartella / "elenco.txt"
    righe = []
    for (file, t), (_, dopo) in zip(fotogrammi, fotogrammi[1:] + [(None, fotogrammi[-1][1] + 1.5)]):
        righe += [f"file '{file.name}'", f"duration {max(dopo - t, 1 / 60):.4f}"]
    righe.append(f"file '{fotogrammi[-1][0].name}'")
    elenco.write_text("\n".join(righe) + "\n")
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(elenco),
                    "-vf", "fps=30,format=yuv420p", "-c:v", "libx264", "-preset", "slow", "-crf", "16",
                    "-movflags", "+faststart", str(uscita)], check=True, cwd=cartella)


def chiama(percorso, metodo="GET"):
    return urllib.request.urlopen(urllib.request.Request(INDIRIZZO + percorso, method=metodo), timeout=10)


def main():
    try:
        chiama("/api/stato")
    except OSError:
        sys.exit("L'applicazione non risponde: accendila con ./demo avvia e riprova.")
    USCITA.mkdir(parents=True, exist_ok=True)
    uscita = USCITA / "demo_fatture.mp4"
    cartella = Path(tempfile.mkdtemp(prefix="fotogrammi_"))
    try:
        chiama("/api/reset", "POST")
        print("Registro la demo (circa due minuti):")
        fotogrammi = asyncio.run(registra(cartella))
        print(f"Monto {len(fotogrammi)} fotogrammi…")
        monta(fotogrammi, cartella, uscita)
        durata = fotogrammi[-1][1] - fotogrammi[0][1] + 1.5
        print(f"Video: video/{uscita.name} ({durata:.0f} secondi, {uscita.stat().st_size / 1e6:.1f} MB)")
    finally:
        shutil.rmtree(cartella, ignore_errors=True)
        try:
            chiama("/api/reset", "POST")
        except OSError:
            pass


if __name__ == "__main__":
    main()
