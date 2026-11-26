#!/usr/bin/env python3
"""Genera 12 mesi di fatture passive inventate (tracciato FatturaPA FPR12) per un centro estetico.
Dati dimostrativi: impresa, fornitori, partite IVA e prezzi sono inventati."""
import random, shutil, csv, sys
from datetime import date, timedelta
from decimal import Decimal as D, ROUND_HALF_UP
from pathlib import Path
from xml.sax.saxutils import escape

random.seed(46)
OUT = Path(sys.argv[1]); shutil.rmtree(OUT, ignore_errors=True); OUT.mkdir(parents=True)
q2 = lambda x: D(x).quantize(D("0.01"), rounding=ROUND_HALF_UP)
MESI = [(2025,11),(2025,12)] + [(2026,m) for m in range(1,11)]
NOMI_MESE = ["","gennaio","febbraio","marzo","aprile","maggio","giugno","luglio","agosto","settembre","ottobre","novembre","dicembre"]

CLIENTE = dict(nome="Brezza Estetica S.r.l.", piva="09999000019", ind="Via dell'Esempio 8", cap="04100", comune="Latina", prov="LT")
# chiave: (nome, piva, indirizzo, cap, comune, prov, regione, categoria, giorni pagamento, modalita)
F = {
 "linea": ("Linea Pelle Distribuzione S.r.l.","09999000101","Via dei Fornitori 21","00100","Roma","RM","Lazio","Prodotti per trattamenti",30,"MP05"),
 "nail":  ("Nail Point Italia S.r.l.","09999000102","Via delle Unghie 4","80100","Napoli","NA","Campania","Unghie",0,"MP05"),
 "bpro":  ("Beauty Pro Forniture S.r.l.","09999000103","Via del Commercio 15","04100","Latina","LT","Lazio","Monouso e consumabili",60,"MP05"),
 "laser": ("MedLaser Rent S.r.l.","09999000104","Viale della Tecnica 9","20100","Milano","MI","Lombardia","Noleggio macchinari",0,"MP19"),
 "tecno": ("TecnoBeauty Noleggi S.r.l.","09999000105","Via dei Macchinari 3","40100","Bologna","BO","Emilia-Romagna","Noleggio macchinari",0,"MP19"),
 "luce":  ("Luce Pontina Energia S.p.A.","09999000106","Corso dell'Energia 1","04100","Latina","LT","Lazio","Energia e acqua",20,"MP19"),
 "acqua": ("Acquedotto Pontino S.p.A.","09999000107","Via dell'Acqua 12","04100","Latina","LT","Lazio","Energia e acqua",30,"MP19"),
 "tel":   ("FibraTel S.p.A.","09999000108","Via delle Reti 50","20100","Milano","MI","Lombardia","Telefonia e internet",15,"MP19"),
 "agenda":("AgendaBella S.r.l.","09999000109","Corso Digitale 7","10100","Torino","TO","Piemonte","Software e incassi",0,"MP08"),
 "pos":   ("PagoFacile S.p.A.","09999000110","Piazza dei Pagamenti 2","20100","Milano","MI","Lombardia","Software e incassi",0,"MP19"),
 "affitto":("Immobiliare Circeo S.r.l.","09999000111","Via del Mare 30","04100","Latina","LT","Lazio","Affitto",5,"MP05"),
 "lav":   ("Lavanderia Industriale Tirrena S.n.c.","09999000112","Via Appia 210","04019","Terracina","LT","Lazio","Lavanderia",30,"MP05"),
 "conta": ("Centro Servizi Contabili Latina S.r.l.","09999000113","Via dei Conti 6","04100","Latina","LT","Lazio","Consulenze",30,"MP05"),
 "acc":   ("Accademia Estetica Avanzata S.r.l.","09999000114","Via della Formazione 18","00100","Roma","RM","Lazio","Formazione",0,"MP05"),
 "puli":  ("Pulito Subito Soc. Coop.","09999000115","Via dell'Ordine 11","04100","Latina","LT","Lazio","Pulizie",30,"MP05"),
 "caffe": ("Caffè Service Latina S.r.l.","09999000116","Via del Ristoro 5","04100","Latina","LT","Lazio","Accoglienza clienti",30,"MP05"),
 "dermo": ("Dermovita Cosmetici S.p.A.","09999000117","Via dei Laboratori 40","50100","Firenze","FI","Toscana","Prodotti per rivendita",60,"MP05"),
 "web":   ("Stampa e Web Latina S.r.l.","09999000118","Via della Tipografia 2","04100","Latina","LT","Lazio","Pubblicità",30,"MP05"),
 "clima": ("ClimaService Pontino S.r.l.","09999000119","Via del Fresco 14","04011","Aprilia","LT","Lazio","Manutenzioni",30,"MP05"),
}
fatture = []   # dict(forn, data, numero, tipo, righe=[(descr, qta, um, prezzo, iva, natura)], causale)
contatori = {}
def num(k, anno, fmt="{n}/{a}"):
    contatori[(k,anno)] = contatori.get((k,anno), random.randint(40, 900)) + random.randint(3, 60)
    return fmt.format(n=contatori[(k,anno)], a=anno)
def add(k, d, righe, causale=None, tipo="TD01", fmt="{n}/{a}", numero=None):
    fatture.append(dict(forn=k, data=d, numero=numero or num(k, d.year, fmt), tipo=tipo, righe=righe, causale=causale))
def g(a, m, lo, hi): return date(a, m, random.randint(lo, hi))
r = random.randint

COLORI = ["Nude Rosa","Rosso Ciliegia","Bianco Latte","Bordeaux","Rosa Cipria","Nero","Corallo","Verde Salvia","Blu Notte","Lilla"]
PESI   = [10, 8, 6, 5, 5, 3, 3, 2, 2, 2]
CREMA = ["12.50","12.50","12.70","12.70","13.00","13.00","13.35","13.65","13.65","14.00","14.20","14.40"]
CERA = ["9.80","9.80","9.95","9.95","10.20","10.20","10.45","10.70","10.70","10.95","11.10","11.27"]
KWH  = [1180,1290,1310,1220,1120,1040,1090,1720,1890,1940,1760,1150]
POS  = ["240.00","395.00","190.00","205.00","230.00","260.00","330.00","360.00","345.00","210.00","270.00","255.00"]

for i,(a,m) in enumerate(MESI):
    estate = m in (6,7,8,9); feste = m in (11,12)
    # A - prodotti per trattamenti (aumento graduale della cera)
    add("linea", g(a,m,4,12), [
        ("Cera depilatoria liposolubile barattolo 800 ml", r(18,26)+(6 if m in (5,6,7) else 0), "pz", CERA[i], 22, None),
        ("Strisce depilatorie conf. 100 pz", r(6,10), "conf", "3.40", 22, None),
        ("Olio post-epilazione 500 ml", r(2,4), "pz", "7.90", 22, None),
        ("Crema massaggio neutra 1 l", r(6,10), "pz", CREMA[i], 22, None),
        ("Maschera viso alginato 1 kg", r(1,3), "pz", "21.00", 22, None),
        ("Latte detergente 500 ml", r(2,4), "pz", "8.60", 22, None)], fmt="FV{n}/{a}")
    # B - unghie
    cols = sorted(set(random.choices(COLORI, weights=PESI, k=7)), key=COLORI.index)
    righe = [(f"Smalto semipermanente 10 ml – {c}", max(2, round(PESI[COLORI.index(c)]*random.uniform(0.7,1.4))), "pz", "6.90", 22, None) for c in cols]
    if i not in (2, 7, 9, 10):
        righe.append(("Gel costruttore trasparente 50 ml", r(3,5), "pz", "24.00", 22, None))
    righe += [("Base e top coat 15 ml", r(4,6), "pz", "9.50", 22, None),
              ("Lime monouso conf. 50 pz", r(2,3), "conf", "11.00", 22, None),
              ("Remover per semipermanente 1 l", r(1,2), "pz", "8.20", 22, None)]
    add("nail", g(a,m,2,9), righe, fmt="{n}")
    # C - monouso (stesso gel a prezzo più alto in alcuni mesi)
    righe = [("Lenzuolino monouso rotolo 80 m", r(10,16), "pz", "4.90", 22, None),
             ("Slip monouso conf. 100 pz", r(2,4), "conf", "9.80", 22, None),
             ("Guanti in nitrile conf. 100 pz", r(6,10), "conf", "5.60", 22, None),
             ("Cuffie monouso conf. 100 pz", r(1,3), "conf", "4.20", 22, None)]
    if i in (1, 2, 4, 6, 7, 9, 10):
        righe.append(("Gel costruttore trasparente 50 ml", r(2,4), "pz", "28.30", 22, None))
    add("bpro", g(a,m,14,22), righe)
    # D - laser a noleggio
    righe = [("Canone noleggio laser diodo", 1, None, "690.00", 22, None), ("Manutenzione programmata laser", 1, None, "60.00", 22, None)]
    if i % 3 == 1: righe.append(("Gel conduttore per laser 5 l", 2, "pz", "18.00", 22, None))
    add("laser", date(a,m,1), righe, causale=f"Noleggio operativo {NOMI_MESE[m]} {a}", fmt="N{n}-{a}")
    # E - pressoterapia: ritirata a giugno 2026, canone fatturato anche dopo
    righe = [("Canone noleggio pressoterapia", 1, None, "260.00", 22, None)]
    if (a,m) == (2026,6): righe.append(("Ritiro apparecchiatura a fine noleggio", 1, None, "80.00", 22, None))
    add("tecno", date(a,m,3), righe, causale=f"Noleggio {NOMI_MESE[m]} {a}")
    # F - energia: prezzo più alto da luglio 2026
    prezzo = "0.2120" if (a,m) < (2026,7) else "0.2680"
    add("luce", date(a,m,28), [("Energia elettrica – consumo", KWH[i], "kWh", prezzo, 22, None),
                              ("Quota fissa e potenza impegnata", 1, None, "38.00", 22, None)],
        causale=f"Fornitura energia elettrica {NOMI_MESE[m]} {a}", fmt="E{a}-{n}")
    if i % 2 == 1:
        add("acqua", g(a,m,16,20), [("Servizio idrico – consumo", r(21,34), "mc", "2.10", 10, None), ("Quota fissa servizio idrico", 1, None, "9.50", 10, None)], fmt="{a}/{n}")
    # H/I/J - telefonia, software, incassi
    add("tel", date(a,m,10), [("Fibra ufficio – canone mensile", 1, None, "34.90", 22, None), ("SIM aziendale – canone mensile", 2, "pz", "9.90", 22, None)], fmt="{a}{n}")
    add("agenda", date(a,m,2), [("Abbonamento gestionale prenotazioni", 1, None, "49.00", 22, None),
                               ("SMS promemoria appuntamenti – pacchetto 500", 2 if (feste or m in (5,6,7)) else 1, "pz", "22.00", 22, None)], fmt="AB-{n}")
    add("pos", date(a,m,5), [("Canone POS", 1, None, "15.00", 22, None),
                            ("Commissioni su incassi con carta", 1, None, POS[i], 0, "N4")], causale=f"Competenze {NOMI_MESE[m]} {a}", fmt="{n}")
    add("affitto", date(a,m,1), [("Canone di locazione locale commerciale", 1, None, "1400.00", 22, None)], causale=f"Affitto {NOMI_MESE[m]} {a}")
    add("lav", g(a,m,26,28), [("Lavaggio teli e asciugamani", r(120,145) if estate else r(85,112), "kg", "1.90", 22, None),
                             ("Noleggio accappatoi", r(34,42) if estate else r(20,30), "pz", "1.20", 22, None)])
    add("conta", g(a,m,25,28), [("Elaborazione buste paga", 3, "pz", "28.00", 22, None)])
    if m in (12,3,6,9):
        add("conta", g(a,m,20,24), [("Tenuta contabilità – trimestre", 1, None, "480.00", 22, None)])
    add("puli", g(a,m,27,28), [("Pulizie locali – canone mensile", 1, None, "220.00", 22, None)])
    add("web", g(a,m,15,20), [("Gestione pagine social – canone mensile", 1, None, "150.00", 22, None)] +
        ([("Buoni regalo stampati", 500, "pz", "0.18", 22, None)] if (a,m)==(2025,11) else []) +
        ([("Volantini promozione estate", 2000, "pz", "0.06", 22, None)] if (a,m)==(2026,4) else []))
    if i % 2 == 0:
        add("caffe", g(a,m,8,14), [("Capsule caffè conf. 100 pz", r(3,5), "conf", "24.00", 22, None),
                                  ("Tisane assortite conf. 20 filtri", r(4,8), "conf", "3.20", 22, None),
                                  ("Acqua naturale 0,5 l conf. 24 pz", r(6,12), "conf", "4.10", 22, None)])

# Q - prodotti per rivendita, con picco a Natale e una nota di credito
def dermo(a, m, extra):
    add("dermo", g(a,m,6,18), [("Crema viso idratante 50 ml", r(8,14), "pz", "14.50", 22, None),
                              ("Siero viso 30 ml", r(5,9), "pz", "19.00", 22, None),
                              ("Crema corpo 200 ml", r(6,12), "pz", "11.00", 22, None)] + extra, fmt="{a}-{n}")
dermo(2025,11,[("Cofanetto regalo Natale", 40, "pz", "22.00", 22, None)])
dermo(2025,12,[("Cofanetto regalo Natale", 15, "pz", "22.00", 22, None)])
add("dermo", date(2026,1,20), [("Reso cofanetto regalo Natale", 8, "pz", "22.00", 22, None)], causale="Nota di credito per reso merce", tipo="TD04", fmt="NC{a}-{n}")
dermo(2026,2,[]); dermo(2026,4,[])
dermo(2026,5,[("Solare viso e corpo SPF50 150 ml", 36, "pz", "9.80", 22, None)])
dermo(2026,7,[("Solare viso e corpo SPF50 150 ml", 18, "pz", "9.80", 22, None)])
dermo(2026,9,[])
add("acc", date(2026,3,9), [("Corso laminazione ciglia – 1 partecipante", 1, None, "390.00", 22, None)])
add("acc", date(2026,9,14), [("Corso aggiornamento laser", 2, "partecipanti", "280.00", 22, None)])
add("clima", date(2026,5,19), [("Manutenzione e sanificazione climatizzatori", 4, "pz", "45.00", 22, None)])

# Doppione: la fattura Dermovita di novembre 2025 arriva due volte (stesso numero, stessa data, stesso importo)
orig = next(f for f in fatture if f["forn"]=="dermo" and f["data"].month==11 and f["data"].year==2025)
fatture.append(dict(orig, doppione=True))

fatture.sort(key=lambda f: (f["data"], f["forn"], f.get("doppione", False)))

def anag(tag, nome, piva, ind, cap, comune, prov, regime=False):
    return (f"<{tag}><DatiAnagrafici><IdFiscaleIVA><IdPaese>IT</IdPaese><IdCodice>{piva}</IdCodice></IdFiscaleIVA>"
            f"<Anagrafica><Denominazione>{escape(nome)}</Denominazione></Anagrafica>{'<RegimeFiscale>RF01</RegimeFiscale>' if regime else ''}</DatiAnagrafici>"
            f"<Sede><Indirizzo>{escape(ind)}</Indirizzo><CAP>{cap}</CAP><Comune>{escape(comune)}</Comune><Provincia>{prov}</Provincia><Nazione>IT</Nazione></Sede></{tag}>")

prog = {}
for f in fatture:
    nome,piva,ind,cap,comune,prov,reg,cat,gg,mod = F[f["forn"]]
    prog[piva] = prog.get(piva, 0) + 1
    progressivo = f"{prog[piva]:05d}"
    linee, riep = [], {}
    for n,(descr,qta,um,prezzo,iva,natura) in enumerate(f["righe"], 1):
        tot = q2(D(prezzo) * D(qta))
        riep.setdefault((iva,natura), D(0)); riep[(iva,natura)] += tot
        linee.append(f"<DettaglioLinee><NumeroLinea>{n}</NumeroLinea><Descrizione>{escape(descr)}</Descrizione>"
                     f"<Quantita>{D(qta):.2f}</Quantita>" + (f"<UnitaMisura>{um}</UnitaMisura>" if um else "") +
                     f"<PrezzoUnitario>{D(prezzo):.4f}</PrezzoUnitario><PrezzoTotale>{tot:.2f}</PrezzoTotale>"
                     f"<AliquotaIVA>{D(iva):.2f}</AliquotaIVA>" + (f"<Natura>{natura}</Natura>" if natura else "") + "</DettaglioLinee>")
    imponibile = sum(riep.values()); imposta_tot = D(0); riepiloghi = []
    for (iva,natura),imp in sorted(riep.items(), key=lambda x: -x[0][0]):
        imposta = q2(imp * D(iva) / 100); imposta_tot += imposta
        riepiloghi.append(f"<DatiRiepilogo><AliquotaIVA>{D(iva):.2f}</AliquotaIVA>" + (f"<Natura>{natura}</Natura>" if natura else "") +
                          f"<ImponibileImporto>{imp:.2f}</ImponibileImporto><Imposta>{imposta:.2f}</Imposta>" +
                          ("<EsigibilitaIVA>I</EsigibilitaIVA>" if not natura else "<RiferimentoNormativo>Esente art. 10 DPR 633/72</RiferimentoNormativo>") + "</DatiRiepilogo>")
    totale = imponibile + imposta_tot
    scad = f["data"] + timedelta(days=gg)
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<p:FatturaElettronica versione="FPR12" xmlns:p="http://ivaservizi.agenziaentrate.gov.it/docs/xsd/fatture/v1.2" '
           'xmlns:ds="http://www.w3.org/2000/09/xmldsig#" xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance">'
           f"<FatturaElettronicaHeader><DatiTrasmissione><IdTrasmittente><IdPaese>IT</IdPaese><IdCodice>{piva}</IdCodice></IdTrasmittente>"
           f"<ProgressivoInvio>{progressivo}</ProgressivoInvio><FormatoTrasmissione>FPR12</FormatoTrasmissione><CodiceDestinatario>0000000</CodiceDestinatario></DatiTrasmissione>"
           + anag("CedentePrestatore", nome, piva, ind, cap, comune, prov, True)
           + anag("CessionarioCommittente", CLIENTE["nome"], CLIENTE["piva"], CLIENTE["ind"], CLIENTE["cap"], CLIENTE["comune"], CLIENTE["prov"])
           + "</FatturaElettronicaHeader><FatturaElettronicaBody><DatiGenerali><DatiGeneraliDocumento>"
           f"<TipoDocumento>{f['tipo']}</TipoDocumento><Divisa>EUR</Divisa><Data>{f['data'].isoformat()}</Data><Numero>{escape(f['numero'])}</Numero>"
           f"<ImportoTotaleDocumento>{totale:.2f}</ImportoTotaleDocumento>" + (f"<Causale>{escape(f['causale'])}</Causale>" if f["causale"] else "") +
           "</DatiGeneraliDocumento></DatiGenerali><DatiBeniServizi>" + "".join(linee) + "".join(riepiloghi) + "</DatiBeniServizi>"
           f"<DatiPagamento><CondizioniPagamento>TP02</CondizioniPagamento><DettaglioPagamento><ModalitaPagamento>{mod}</ModalitaPagamento>"
           f"<DataScadenzaPagamento>{scad.isoformat()}</DataScadenzaPagamento><ImportoPagamento>{totale:.2f}</ImportoPagamento></DettaglioPagamento></DatiPagamento>"
           "</FatturaElettronicaBody></p:FatturaElettronica>\n")
    (OUT / f"IT{piva}_{progressivo}.xml").write_text(xml, encoding="utf-8")

with open(OUT.parent / "fornitori.csv", "w", newline="", encoding="utf-8") as fh:
    w = csv.writer(fh); w.writerow(["partita_iva","fornitore","comune","provincia","regione","categoria"])
    for nome,piva,ind,cap,comune,prov,reg,cat,gg,mod in F.values(): w.writerow([piva,nome,comune,prov,reg,cat])
print(len(fatture), "fatture scritte in", OUT)
