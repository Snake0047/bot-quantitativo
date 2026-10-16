"""Il giro giornaliero: scarica, decide, registra, avvisa.

Idempotente: se il giro di oggi è già stato fatto per quello strumento, non
scrive niente e non manda niente. Così un timer che parte due volte, o un
riavvio del server, non sporcano il registro.

Non manda un messaggio al giorno: manda un messaggio quando la posizione
CAMBIA. Un bot che scrive tutti i giorni "nessuna novità" si silenzia dopo
una settimana, e allora non serve più a niente.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path

import pandas as pd

from . import avvisi, dati, strategie
from .backtest import Costi
from .rischio import Bloccato, Guardia, Limiti
from .validazione import scegli

RADICE = Path(__file__).resolve().parent.parent
STATO = RADICE / "dati" / "stato.json"
DIARIO = RADICE / "dati" / "diario.jsonl"

# parametri ricalibrati ogni RICALIBRA giorni sulle ultime BARRE_IS barre
RICALIBRA = 63
BARRE_IS = 1008


@dataclass
class Decisione:
    simbolo: str
    data: str
    prezzo: float
    peso: float
    peso_prima: float
    parametri: dict
    strategia: str
    motivo: str

    def riga(self) -> dict:
        return {"quando": datetime.now(timezone.utc).isoformat(), **self.__dict__}


def _stato() -> dict:
    if STATO.exists():
        try:
            return json.loads(STATO.read_text())
        except json.JSONDecodeError:
            pass
    return {}


def _salva_stato(s: dict) -> None:
    STATO.parent.mkdir(parents=True, exist_ok=True)
    tmp = STATO.with_suffix(".tmp")
    tmp.write_text(json.dumps(s, indent=2, ensure_ascii=False))
    tmp.replace(STATO)          # scrittura atomica: niente stato mezzo scritto


def _appendi(riga: dict) -> None:
    DIARIO.parent.mkdir(parents=True, exist_ok=True)
    with DIARIO.open("a", encoding="utf-8") as f:
        f.write(json.dumps(riga, ensure_ascii=False) + "\n")


def _freccia(prima: float, dopo: float) -> str:
    if dopo > prima + 1e-9:
        return "ENTRA" if prima <= 1e-9 else "AUMENTA"
    if dopo < prima - 1e-9:
        return "ESCE" if dopo <= 1e-9 else "RIDUCE"
    return "FERMO"


def giro(simbolo: str, nome_strategia: str = "trend",
         costi: Costi = Costi(), forza: bool = False) -> Decisione | None:
    s = {x.nome: x for x in strategie.TUTTE}[nome_strategia]
    stato = _stato()
    chiave = f"{simbolo}:{nome_strategia}"
    mio = stato.get(chiave, {})

    df = dati.carica(simbolo, riusa=False)
    oggi = str(df.index[-1].date())
    if not forza and mio.get("ultima_barra") == oggi:
        return None                       # già fatto per questa barra

    # ricalibrazione periodica, sempre su dati passati
    giri = mio.get("giri_da_calibrazione", RICALIBRA)
    par = mio.get("parametri")
    if par is None or giri >= RICALIBRA:
        par, _ = scegli(s, df.iloc[-BARRE_IS:], costi)
        giri = 0

    pos = strategie.dimensiona(s.segnale(df, par), df)
    voluto = float(pos.iloc[-1])
    prima = float(mio.get("peso", 0.0))

    guardia = Guardia(Limiti())
    guardia.picco = float(mio.get("picco", 1.0))
    try:
        peso = guardia.filtra(voluto)
        motivo = _freccia(prima, peso)
    except Bloccato as e:
        peso, motivo = 0.0, f"BLOCCATO: {e}"

    d = Decisione(simbolo, oggi, float(df["chiusura"].iloc[-1]), round(peso, 4),
                  round(prima, 4), par, nome_strategia, motivo)
    _appendi(d.riga())
    stato[chiave] = {"ultima_barra": oggi, "peso": peso, "parametri": par,
                     "giri_da_calibrazione": giri + 1, "picco": guardia.picco}
    _salva_stato(stato)
    return d


def messaggio(d: Decisione) -> str:
    return (f"<b>{d.simbolo}</b> · {d.motivo}\n"
            f"{d.data} · {d.prezzo:,.2f}\n"
            f"peso {d.peso_prima:.0%} → <b>{d.peso:.0%}</b>\n"
            f"<i>{d.strategia} {json.dumps(d.parametri)}</i>\n"
            f"conto di carta: nessun ordine reale")


def esegui(simboli: list[str], strategia: str = "trend",
           forza: bool = False, sempre: bool = False) -> list[Decisione]:
    fatte = []
    for sim in simboli:
        try:
            d = giro(sim, strategia, forza=forza)
        except Exception as e:                      # un simbolo rotto non ferma gli altri
            avvisi.manda(f"⚠️ <b>{sim}</b>: {type(e).__name__}: {e}")
            continue
        if d is None:
            continue
        fatte.append(d)
        if sempre or d.motivo != "FERMO":
            avvisi.manda(messaggio(d), silenzioso=(d.motivo == "FERMO"))
    return fatte


def riassunto(giorni: int = 7) -> str:
    """Cosa è successo nell'ultima settimana, dal diario."""
    if not DIARIO.exists():
        return "Nessun giro registrato."
    righe = [json.loads(r) for r in DIARIO.read_text().splitlines() if r.strip()]
    limite = pd.Timestamp.now(tz="UTC") - pd.Timedelta(days=giorni)
    recenti = [r for r in righe if pd.Timestamp(r["quando"]) >= limite]
    mosse = [r for r in recenti if r["motivo"] != "FERMO"]
    testo = [f"<b>Ultimi {giorni} giorni</b>",
             f"giri: {len(recenti)} · movimenti: {len(mosse)}"]
    for r in mosse[-10:]:
        testo.append(f"· {r['data']} {r['simbolo']} {r['motivo']} "
                     f"{r['peso_prima']:.0%}→{r['peso']:.0%}")
    if not mosse:
        testo.append("nessun movimento: posizioni invariate")
    testo.append(f"\ntotale decisioni registrate: {len(righe)}")
    return "\n".join(testo)
