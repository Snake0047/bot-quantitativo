"""Strategie dietro un'unica interfaccia.

Una strategia è: una griglia di parametri + una funzione che, dati i
parametri, trasforma un DataFrame in una posizione in [0, 1].

Il segnale NON sfasa: lo sfasamento di una barra lo applica il backtest,
in un punto solo, così non può essere dimenticato.
"""
from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from typing import Callable, Iterator

import pandas as pd

from .indicatori import donchian, media, volatilita, zscore


@dataclass(frozen=True)
class Strategia:
    nome: str
    griglia: dict[str, tuple]
    _segnale: Callable[[pd.DataFrame, dict], pd.Series]

    def combinazioni(self) -> Iterator[dict]:
        chiavi = list(self.griglia)
        for valori in product(*(self.griglia[k] for k in chiavi)):
            yield dict(zip(chiavi, valori))

    @property
    def n_combinazioni(self) -> int:
        n = 1
        for v in self.griglia.values():
            n *= len(v)
        return n

    def segnale(self, df: pd.DataFrame, par: dict) -> pd.Series:
        s = self._segnale(df, par).reindex(df.index).fillna(0.0)
        return s.clip(0.0, 1.0)


def _trend(df: pd.DataFrame, p: dict) -> pd.Series:
    px = df["chiusura"]
    mv, ml = media(px, p["veloce"]), media(px, p["lenta"])
    return ((mv > ml) & (px > ml)).astype(float)


def _ritorno_media(df: pd.DataFrame, p: dict) -> pd.Series:
    """Compra lo scostamento negativo, ma solo sopra il trend di lungo."""
    px = df["chiusura"]
    z = zscore(px, p["finestra"])
    regime = px > media(px, p["regime"])
    return ((z < -p["soglia"]) & regime).astype(float)


def _breakout(df: pd.DataFrame, p: dict) -> pd.Series:
    """Dentro al superamento del massimo a n giorni, fuori al minimo a m."""
    alto, _ = donchian(df, p["entrata"])
    _, basso = donchian(df, p["uscita"])
    px = df["chiusura"]
    stato, dentro = [], 0.0
    for c, a, b in zip(px.values, alto.values, basso.values):
        if dentro == 0.0 and a == a and c > a:
            dentro = 1.0
        elif dentro == 1.0 and b == b and c < b:
            dentro = 0.0
        stato.append(dentro)
    return pd.Series(stato, index=px.index)


TREND = Strategia("trend", {"veloce": (10, 20, 50), "lenta": (100, 150, 200)}, _trend)
RITORNO = Strategia("ritorno_media",
                    {"finestra": (5, 10, 20), "soglia": (1.0, 1.5, 2.0), "regime": (200,)},
                    _ritorno_media)
BREAKOUT = Strategia("breakout", {"entrata": (20, 55, 100), "uscita": (10, 20, 50)}, _breakout)

TUTTE = (TREND, RITORNO, BREAKOUT)


def dimensiona(segnale: pd.Series, df: pd.DataFrame,
               vol_bersaglio: float = 0.15, massimo: float = 1.0) -> pd.Series:
    """Scala la posizione a volatilità bersaglio, con vol stimata sul passato."""
    v = volatilita(df["chiusura"]).shift(1)
    return (segnale * (vol_bersaglio / v).clip(upper=massimo)).fillna(0.0)
