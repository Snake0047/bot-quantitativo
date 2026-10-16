"""Le prove che separano una strategia da una curva sovradattata.

1. walk_forward  — i parametri si scelgono SOLO sul passato di ogni finestra
                   e si misurano SOLO sul futuro immediato.
2. permutazione  — quanto dello Sharpe sopravvive mescolando i rendimenti.
3. deflaziona    — quanto Sharpe produce da solo il numero di varianti provate.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from .backtest import BARRE_ANNO, Costi, Esito, esegui, misura, rendimenti
from .strategie import Strategia, dimensiona

SCALDATA = 260   # barre di riscaldamento per gli indicatori più lenti


@dataclass(frozen=True)
class Finestra:
    fine: pd.Timestamp
    parametri: dict
    sharpe_is: float
    sharpe_oos: float


def _posizione(s: Strategia, df: pd.DataFrame, par: dict) -> pd.Series:
    return dimensiona(s.segnale(df, par), df)


def scegli(s: Strategia, df: pd.DataFrame, costi: Costi) -> tuple[dict, float]:
    """Il miglior parametro in campione. Parità risolta dal Calmar."""
    migliore, punteggio = None, -np.inf
    for par in s.combinazioni():
        _, e = esegui(df, _posizione(s, df, par), costi)
        if e.barre and e.sharpe > punteggio:
            migliore, punteggio = par, e.sharpe
    return (migliore or next(s.combinazioni())), float(punteggio)


def walk_forward(s: Strategia, df: pd.DataFrame, barre_is: int = 1008,
                 barre_oos: int = 126, costi: Costi = Costi()
                 ) -> tuple[pd.Series, list[Finestra], Esito]:
    pezzi, finestre = [], []
    i = barre_is
    while i + barre_oos <= len(df):
        dentro = df.iloc[i - barre_is:i]
        par, sh_is = scegli(s, dentro, costi)

        # la coda serve a far scaldare gli indicatori senza vedere il futuro
        da = max(0, i - SCALDATA)
        fuori = df.iloc[da:i + barre_oos]
        pos = _posizione(s, fuori, par).iloc[i - da:]
        r = rendimenti(df.iloc[i:i + barre_oos], pos, costi)

        pezzi.append(r)
        finestre.append(Finestra(df.index[i + barre_oos - 1], par, sh_is,
                                 misura(r).sharpe))
        i += barre_oos

    if not pezzi:
        return pd.Series(dtype=float), [], misura(pd.Series(dtype=float))
    rend = pd.concat(pezzi)
    return (1 + rend).cumprod(), finestre, misura(rend)


def permutazione(s: Strategia, df: pd.DataFrame, par: dict, n: int = 400,
                 seme: int = 11, costi: Costi = Costi()) -> dict:
    _, vero = esegui(df, _posizione(s, df, par), costi)
    r = np.random.default_rng(seme)
    rend = df["chiusura"].pct_change().dropna().values
    base = float(df["chiusura"].iloc[0])
    finti = np.empty(n)
    for k in range(n):
        px = pd.Series(np.r_[base, base * np.cumprod(1 + r.permutation(rend))],
                       index=df.index[:len(rend) + 1])
        finto = pd.DataFrame({"apertura": px, "massimo": px, "minimo": px,
                              "chiusura": px, "volume": 1.0})
        _, e = esegui(finto, _posizione(s, finto, par), costi)
        finti[k] = e.sharpe
    return {"sharpe_vero": vero.sharpe, "rumore_medio": float(finti.mean()),
            "rumore_p95": float(np.percentile(finti, 95)),
            "p": float((finti >= vero.sharpe).mean()), "n": n}


def _inv_norm(p: float) -> float:
    a = [-3.969683028665376e+01, 2.209460984245205e+02, -2.759285104469687e+02,
         1.383577518672690e+02, -3.066479806614716e+01, 2.506628277459239e+00]
    b = [-5.447609879822406e+01, 1.615858368580409e+02, -1.556989798598866e+02,
         6.680131188771972e+01, -1.328068155288572e+01]
    c = [-7.784894002430293e-03, -3.223964580411365e-01, -2.400758277161838e+00,
         -2.549732539343734e+00, 4.374664141464968e+00, 2.938163982698783e+00]
    d = [7.784695709041462e-03, 3.224671290700398e-01, 2.445134137142996e+00,
         3.754408661907416e+00]
    pl, ph = 0.02425, 1 - 0.02425
    if p < pl:
        q = np.sqrt(-2 * np.log(p))
        return (((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    if p > ph:
        q = np.sqrt(-2 * np.log(1 - p))
        return -(((((c[0]*q+c[1])*q+c[2])*q+c[3])*q+c[4])*q+c[5]) / ((((d[0]*q+d[1])*q+d[2])*q+d[3])*q+1)
    q = p - 0.5
    rr = q * q
    return (((((a[0]*rr+a[1])*rr+a[2])*rr+a[3])*rr+a[4])*rr+a[5])*q / (((((b[0]*rr+b[1])*rr+b[2])*rr+b[3])*rr+b[4])*rr+1)


def sharpe_da_rumore(n_prove: int, n_barre: int) -> float:
    """Sharpe atteso dalla migliore di n_prove varianti su pura fortuna."""
    if n_prove < 2 or n_barre < 2:
        return 0.0
    g = 0.5772156649
    z = (1 - g) * _inv_norm(1 - 1 / n_prove) + g * _inv_norm(1 - 1 / (n_prove * np.e))
    return float(z / np.sqrt(n_barre / BARRE_ANNO))


def deflaziona(sharpe: float, n_prove: int, n_barre: int) -> float:
    return float(sharpe - sharpe_da_rumore(n_prove, n_barre))
