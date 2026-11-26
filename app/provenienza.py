"""Provenienza: dalle interrogazioni di una domanda ricava le fatture che compongono la cifra.

Dall'ultima interrogazione riuscita si prende la SELECT che legge le fatture o le righe, se ne tengono
tabelle e filtro, e si chiede alla base dati quali fatture passano quel filtro.
"""
import sqlglot
from sqlglot import exp

from .strumenti import Dati, ErroreInterrogazione

_RIGHE = {"righe_valide", "righe"}
_FATTURE = {"fatture_valide", "fatture"}
MASSIMO = 200


def _tabelle_dirette(select: exp.Select) -> list[exp.Table]:
    tabelle = []
    da = select.args.get("from") or select.args.get("from_")
    if da is not None and isinstance(da.this, exp.Table):
        tabelle.append(da.this)
    for j in select.args.get("joins") or []:
        if isinstance(j.this, exp.Table):
            tabelle.append(j.this)
    return tabelle


def _interrogazione_fatture(select: exp.Select) -> str | None:
    tabelle = _tabelle_dirette(select)
    righe = next((t for t in tabelle if t.name.lower() in _RIGHE), None)
    fatture = next((t for t in tabelle if t.name.lower() in _FATTURE), None)
    if righe is None and fatture is None:
        return None
    if righe is not None:
        a = righe.alias_or_name
        colonne = f"{a}.fattura_id AS fid, SUM({a}.importo) AS importo"
    else:
        a = fatture.alias_or_name
        colonne = f"{a}.id AS fid, SUM({a}.imponibile) AS importo"
    da = select.args.get("from") or select.args.get("from_")
    pezzi = [f"SELECT {colonne}", da.sql(dialect="sqlite")]
    pezzi += [j.sql(dialect="sqlite") for j in select.args.get("joins") or []]
    if select.args.get("where") is not None:
        pezzi.append(select.args["where"].sql(dialect="sqlite"))
    pezzi.append("GROUP BY 1")
    interna = " ".join(pezzi)
    return ("SELECT f.fornitore, f.numero, f.data, x.importo, f.file FROM (" + interna + ") x "
            "JOIN fatture f ON f.id = x.fid ORDER BY f.data, f.id")


def fatture_coinvolte(dati: Dati, sql: str) -> list[dict] | None:
    """Le fatture lette dall'interrogazione, o None se non si riesce a ricostruirle."""
    try:
        albero = sqlglot.parse_one(sql, read="sqlite")
    except Exception:
        return None
    for select in albero.find_all(exp.Select):
        try:
            derivata = _interrogazione_fatture(select)
            if derivata is None:
                continue
            ris = dati.interroga(derivata, righe_massime=MASSIMO)
        except (ErroreInterrogazione, Exception):
            continue
        return [{"fornitore": r[0], "numero": r[1], "data": r[2], "importo": round(r[3] or 0, 2), "file": r[4]}
                for r in ris["righe"]]
    return None


def da_analisi(testo: str, analisi: dict) -> list[dict]:
    """Per una risposta presa dalla prima analisi: le fatture dei casi di cui il testo parla."""
    casi = [c for regola in ("doppioni", "canoni_dopo_fine", "aumenti", "prezzi_diversi") for c in analisi.get(regola, [])]
    basso = testo.lower()

    def citato(caso) -> bool:
        nomi = [caso.get("fornitore"), caso.get("fornitore_caro")]
        return any(n and n.split(" S.")[0].lower() in basso for n in nomi)

    viste, fatture = set(), []
    for caso in [c for c in casi if citato(c)] or casi:
        for f in caso.get("fatture", []):
            chiave = (f["file"], f["importo"])
            if chiave not in viste:
                viste.add(chiave)
                fatture.append(f)
    return sorted(fatture, key=lambda f: f["data"])
