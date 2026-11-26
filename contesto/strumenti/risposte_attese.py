#!/usr/bin/env python3
"""Calcola dal database i numeri attesi per le storie e le domande di prova."""
import json, sys
sys.path.insert(0, __file__.rsplit("/",1)[0])
from carica_fatture import carica
db = carica(sys.argv[1], sys.argv[2], sys.argv[3])
def q(sql, *p): return db.execute(sql, p).fetchall()
def uno(sql, *p): return db.execute(sql, p).fetchone()[0]
r2 = lambda x: round(x, 2)
R = {}
R["periodo"] = list(uno("SELECT MIN(data)||' / '||MAX(data) FROM fatture").split(" / "))
R["file_caricati"] = uno("SELECT COUNT(*) FROM fatture")
R["fatture_valide"] = uno("SELECT COUNT(*) FROM fatture_valide")
R["fornitori"] = uno("SELECT COUNT(DISTINCT partita_iva) FROM fatture")
tot = uno("SELECT SUM(imponibile) FROM fatture_valide"); R["spesa_totale_imponibile"] = r2(tot)
R["iva_totale"] = r2(uno("SELECT SUM(iva) FROM fatture_valide")); R["totale_con_iva"] = r2(uno("SELECT SUM(totale) FROM fatture_valide"))
R["spesa_per_categoria"] = [dict(categoria=c, spesa=r2(s), quota_percento=round(100*s/tot,1)) for c,s in q("SELECT categoria, SUM(imponibile) s FROM fatture_valide GROUP BY 1 ORDER BY s DESC")]
R["spesa_per_fornitore"] = [dict(fornitore=c, spesa=r2(s), fatture=n) for c,s,n in q("SELECT fornitore, SUM(imponibile) s, COUNT(*) FROM fatture_valide GROUP BY 1 ORDER BY s DESC")]
R["spesa_per_mese"] = [dict(mese=m, spesa=r2(s)) for m,s in q("SELECT mese, SUM(imponibile) FROM fatture_valide GROUP BY 1 ORDER BY 1")]
# storia 1: aumenti graduali dello stesso fornitore
def aumento(like):
    serie = q("SELECT mese, prezzo_unitario, quantita, articolo FROM righe_valide WHERE articolo LIKE ? ORDER BY data", like)
    p0, p1 = serie[0][1], serie[-1][1]
    return dict(articolo=serie[0][3], prezzo_iniziale=p0, prezzo_finale=p1, aumento_percento=round(100*(p1/p0-1),1),
                numero_aumenti=len({p for _,p,_,_ in serie})-1, pezzi=sum(c[2] for c in serie),
                maggior_costo=r2(sum(qt*(p-p0) for _,p,qt,_ in serie)), maggior_costo_annuo_a_prezzo_finale=r2(sum(c[2] for c in serie)*(p1-p0)),
                serie=[dict(mese=m, prezzo=p) for m,p,_,_ in serie])
R["aumenti"] = dict(fornitore="Linea Pelle Distribuzione S.r.l.", articoli=[aumento("Cera depilatoria%"), aumento("Crema massaggio%")])
R["aumenti"]["maggior_costo_totale"] = r2(sum(a["maggior_costo"] for a in R["aumenti"]["articoli"]))
R["aumenti"]["maggior_costo_annuo_a_prezzi_finali"] = r2(sum(a["maggior_costo_annuo_a_prezzo_finale"] for a in R["aumenti"]["articoli"]))
R["articoli_con_prezzo_variato"] = [dict(fornitore=f, articolo=a, minimo=mi, massimo=ma) for f,a,mi,ma in q("SELECT fornitore, articolo, MIN(prezzo_unitario), MAX(prezzo_unitario) FROM righe_valide GROUP BY 1,2 HAVING MIN(prezzo_unitario)<>MAX(prezzo_unitario)")]
# storia 2: stesso gel da due fornitori
gel = q("SELECT fornitore, prezzo_unitario, SUM(quantita), SUM(importo) FROM righe_valide WHERE articolo LIKE 'Gel costruttore%' GROUP BY 1,2 ORDER BY 2")
R["gel"] = dict(dettaglio=[dict(fornitore=f, prezzo=p, pezzi=n, spesa=r2(s)) for f,p,n,s in gel],
                differenza_percento=round(100*(gel[1][1]/gel[0][1]-1),1), risparmio_possibile=r2(gel[1][2]*(gel[1][1]-gel[0][1])))
# storia 3: fattura doppia
d = q("SELECT fornitore, numero, data, imponibile, totale, file FROM fatture WHERE doppione=1")
R["doppione"] = [dict(fornitore=a, numero=b, data=c, imponibile=e, totale=f, file_doppio=g,
                      file_originale=uno("SELECT file FROM fatture WHERE doppione=0 AND numero=? AND fornitore=?", b, a)) for a,b,c,e,f,g in d]
# storia 4: canone dopo il ritiro
rit = uno("SELECT data FROM righe_valide WHERE descrizione LIKE 'Ritiro apparecchiatura%'")
dopo = q("SELECT mese, importo FROM righe_valide WHERE descrizione='Canone noleggio pressoterapia' AND data > ? ORDER BY 1", rit)
R["pressoterapia"] = dict(fornitore="TecnoBeauty Noleggi S.r.l.", data_ritiro=rit, canoni_dopo_il_ritiro=len(dopo), mesi=[m for m,_ in dopo],
                          importo_non_dovuto=r2(sum(i for _,i in dopo)), importo_non_dovuto_con_iva=r2(sum(i for _,i in dopo)*1.22))
R["recuperabile_totale_imponibile"] = r2(R["aumenti"]["maggior_costo_totale"] + R["gel"]["risparmio_possibile"] + R["doppione"][0]["imponibile"] + R["pressoterapia"]["importo_non_dovuto"])
# energia
en = q("SELECT mese, quantita, prezzo_unitario, importo FROM righe_valide WHERE articolo='Energia elettrica – consumo' ORDER BY 1")
R["energia"] = dict(kwh_totali=sum(e[1] for e in en), spesa_totale_luce=r2(uno("SELECT SUM(imponibile) FROM fatture_valide WHERE fornitore LIKE 'Luce%'")),
                    prezzo_kwh_prima=en[0][2], prezzo_kwh_dopo=en[-1][2], primo_mese_nuovo_prezzo=next(e[0] for e in en if e[2]!=en[0][2]),
                    aumento_percento=round(100*(en[-1][2]/en[0][2]-1),1), mese_piu_caro=max(en, key=lambda e:e[3])[0],
                    maggior_costo_da_cambio_prezzo=r2(sum(e[1]*(e[2]-en[0][2]) for e in en)), serie=[dict(mese=e[0], kwh=e[1], prezzo=e[2]) for e in en])
# laser
R["laser"] = dict(spesa_annua=r2(uno("SELECT SUM(imponibile) FROM fatture_valide WHERE fornitore LIKE 'MedLaser%'")),
                  media_mensile=r2(uno("SELECT SUM(imponibile)/12 FROM fatture_valide WHERE fornitore LIKE 'MedLaser%'")), canone=690.0, manutenzione=60.0)
# curiosità
R["smalti"] = dict(boccette=uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'Smalto%'"), spesa=r2(uno("SELECT SUM(importo) FROM righe_valide WHERE articolo LIKE 'Smalto%'")),
                   per_colore=[dict(colore=c, boccette=n) for c,n in q("SELECT variante, SUM(quantita) n FROM righe_valide WHERE articolo LIKE 'Smalto%' GROUP BY 1 ORDER BY n DESC")])
caps = uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'Capsule%'")
R["caffe"] = dict(confezioni=caps, capsule=caps*100, spesa_capsule=r2(uno("SELECT SUM(importo) FROM righe_valide WHERE articolo LIKE 'Capsule%'")),
                  spesa_accoglienza=r2(uno("SELECT SUM(imponibile) FROM fatture_valide WHERE categoria='Accoglienza clienti'")))
R["incassi_e_appuntamenti"] = dict(pos_canoni=r2(uno("SELECT SUM(importo) FROM righe_valide WHERE articolo='Canone POS'")),
    pos_commissioni=r2(uno("SELECT SUM(importo) FROM righe_valide WHERE articolo LIKE 'Commissioni%'")),
    gestionale=r2(uno("SELECT SUM(importo) FROM righe_valide WHERE articolo LIKE 'Abbonamento gestionale%'")),
    sms=r2(uno("SELECT SUM(importo) FROM righe_valide WHERE articolo LIKE 'SMS%'")), pacchetti_sms=uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'SMS%'"),
    totale=r2(uno("SELECT SUM(imponibile) FROM fatture_valide WHERE categoria='Software e incassi'")))
R["cera_barattoli"] = R["aumenti"]["articoli"][0]["pezzi"]
R["lenzuolini_rotoli"] = uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'Lenzuolino%'")
R["lavanderia"] = dict(kg=uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'Lavaggio%'"), spesa=r2(uno("SELECT SUM(imponibile) FROM fatture_valide WHERE categoria='Lavanderia'")))
R["natale"] = dict(cofanetti_comprati=uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo='Cofanetto regalo Natale'"),
                   cofanetti_resi=-uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'Reso cofanetto%'"),
                   nota_di_credito=q("SELECT numero, data, imponibile FROM fatture_valide WHERE tipo_documento='TD04'")[0])
R["solari"] = uno("SELECT SUM(quantita) FROM righe_valide WHERE articolo LIKE 'Solare%'")
R["formazione"] = [dict(data=a, corso=b, importo=c) for a,b,c in q("SELECT data, descrizione, importo FROM righe_valide WHERE categoria='Formazione' ORDER BY 1")]
reg = q("SELECT regione, SUM(imponibile) s, COUNT(DISTINCT partita_iva) FROM fatture_valide GROUP BY 1 ORDER BY s DESC")
R["per_regione"] = [dict(regione=a, spesa=r2(b), quota_percento=round(100*b/tot,1), fornitori=c) for a,b,c in reg]
R["provincia_di_latina"] = dict(spesa=r2(uno("SELECT SUM(imponibile) FROM fatture_valide WHERE provincia='LT'")), quota_percento=round(100*uno("SELECT SUM(imponibile) FROM fatture_valide WHERE provincia='LT'")/tot,1),
                                fornitori=uno("SELECT COUNT(DISTINCT partita_iva) FROM fatture_valide WHERE provincia='LT'"))
R["pagamenti"] = [dict(fornitore=a, giorni=b) for a,b in q("SELECT fornitore, MAX(giorni_pagamento) g FROM fatture_valide GROUP BY 1 ORDER BY g, 1")]
m = q("SELECT fornitore, numero, data, imponibile FROM fatture_valide ORDER BY imponibile DESC LIMIT 1")[0]
R["fattura_piu_grande"] = dict(fornitore=m[0], numero=m[1], data=m[2], imponibile=m[3])
m = q("SELECT fornitore, numero, data, imponibile FROM fatture_valide WHERE imponibile>0 ORDER BY imponibile LIMIT 1")[0]
R["fattura_piu_piccola"] = dict(fornitore=m[0], numero=m[1], data=m[2], imponibile=m[3])
R["mese_piu_caro"] = max(R["spesa_per_mese"], key=lambda x: x["spesa"]); R["mese_meno_caro"] = min(R["spesa_per_mese"], key=lambda x: x["spesa"])
R["costi_fissi_mensili"] = dict(affitto=1400.0, laser=750.0, pulizie=220.0, social=150.0, gestionale=49.0, fibra_e_sim=54.7)
R["noleggi_totale"] = r2(uno("SELECT SUM(imponibile) FROM fatture_valide WHERE categoria='Noleggio macchinari'"))
json.dump(R, open(sys.argv[4], "w", encoding="utf-8"), ensure_ascii=False, indent=2)
for k in ["file_caricati","fatture_valide","fornitori","spesa_totale_imponibile","totale_con_iva","spesa_per_categoria","aumenti","articoli_con_prezzo_variato","gel","doppione","pressoterapia","recuperabile_totale_imponibile","energia","laser","smalti","caffe","incassi_e_appuntamenti","lenzuolini_rotoli","lavanderia","natale","solari","per_regione","provincia_di_latina","pagamenti","spesa_per_fornitore","fattura_piu_grande","fattura_piu_piccola","mese_piu_caro","mese_meno_caro","noleggi_totale"]:
    v = R[k]
    if k=="energia": v = {a:b for a,b in v.items() if a!="serie"}
    if k=="aumenti": v = dict(v, articoli=[{a:b for a,b in x.items() if a!="serie"} for x in v["articoli"]])
    print(k, "=", json.dumps(v, ensure_ascii=False))
