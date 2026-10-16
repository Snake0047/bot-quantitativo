"""Esecuzione. Qui, e solo qui, la posizione viene sfasata di una barra."""
from __future__ import annotations

from dataclasses import asdict, dataclass

import numpy as np
import pandas as pd

BARRE_ANNO = 252


@dataclass(frozen=True)
class Costi:
    commissione: float = 0.0005
    slippage: float = 0.0005

    @property
    def per_lato(self) -> float:
        return self.commissione + self.slippage


@dataclass(frozen=True)
class Esito:
    sharpe: float
    cagr: float
    vol: float
    max_drawdown: float
    calmar: float
    dentro: float
    rotazione_annua: float
    costi: float
    barre: int

    def dizionario(self) -> dict:
        return asdict(self)


VUOTO = Esito(0.0, 0.0, 0.0, 0.0, float("nan"), 0.0, 0.0, 0.0, 0)


def rendimenti(df: pd.DataFrame, posizione: pd.Series, costi: Costi = Costi()) -> pd.Series:
    px = df["chiusura"].astype(float)
    pos = posizione.reindex(px.index).fillna(0.0).astype(float).shift(1).fillna(0.0)
    scambio = pos.diff().abs().fillna(pos.abs())
    return pos * px.pct_change().fillna(0.0) - scambio * costi.per_lato


def misura(rend: pd.Series, pos_eff: pd.Series | None = None,
           costi_tot: float = 0.0) -> Esito:
    if len(rend) < 2 or rend.std() == 0:
        return VUOTO
    eq = (1 + rend).cumprod()
    anni = len(rend) / BARRE_ANNO
    tot = float(eq.iloc[-1])
    dd = float((eq / eq.cummax() - 1).min())
    cagr = tot ** (1 / anni) - 1 if tot > 0 else float("nan")
    return Esito(
        sharpe=float(rend.mean() / rend.std() * np.sqrt(BARRE_ANNO)),
        cagr=float(cagr),
        vol=float(rend.std() * np.sqrt(BARRE_ANNO)),
        max_drawdown=dd,
        calmar=float(cagr / abs(dd)) if dd < 0 else float("nan"),
        dentro=float((pos_eff.abs() > 1e-9).mean()) if pos_eff is not None else float("nan"),
        rotazione_annua=float(pos_eff.diff().abs().sum() / anni) if pos_eff is not None else float("nan"),
        costi=float(costi_tot),
        barre=len(rend),
    )


def esegui(df: pd.DataFrame, posizione: pd.Series,
           costi: Costi = Costi()) -> tuple[pd.Series, Esito]:
    px = df["chiusura"].astype(float)
    pos = posizione.reindex(px.index).fillna(0.0).astype(float).shift(1).fillna(0.0)
    scambio = pos.diff().abs().fillna(pos.abs())
    rend = pos * px.pct_change().fillna(0.0) - scambio * costi.per_lato
    return (1 + rend).cumprod(), misura(rend, pos, float((scambio * costi.per_lato).sum()))


def compra_e_tieni(df: pd.DataFrame) -> tuple[pd.Series, Esito]:
    return esegui(df, pd.Series(1.0, index=df.index), Costi(0.0, 0.0))
