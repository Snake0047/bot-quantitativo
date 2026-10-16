"""Indicatori. Tutti causali: usano solo barre fino a t compresa."""
from __future__ import annotations

import numpy as np
import pandas as pd


def media(px: pd.Series, n: int) -> pd.Series:
    return px.rolling(n, min_periods=n).mean()


def atr(df: pd.DataFrame, n: int = 14) -> pd.Series:
    prec = df["chiusura"].shift(1)
    tr = pd.concat([df["massimo"] - df["minimo"],
                    (df["massimo"] - prec).abs(),
                    (df["minimo"] - prec).abs()], axis=1).max(axis=1)
    return tr.ewm(alpha=1 / n, min_periods=n, adjust=False).mean()


def rsi(px: pd.Series, n: int = 14) -> pd.Series:
    d = px.diff()
    su = d.clip(lower=0).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    giu = (-d.clip(upper=0)).ewm(alpha=1 / n, min_periods=n, adjust=False).mean()
    return (100 - 100 / (1 + su / giu.replace(0, np.nan))).fillna(50)


def volatilita(px: pd.Series, n: int = 20) -> pd.Series:
    return np.log(px).diff().rolling(n, min_periods=n).std() * np.sqrt(252)


def zscore(px: pd.Series, n: int) -> pd.Series:
    m = px.rolling(n, min_periods=n).mean()
    s = px.rolling(n, min_periods=n).std()
    return (px - m) / s.replace(0, np.nan)


def donchian(df: pd.DataFrame, n: int) -> tuple[pd.Series, pd.Series]:
    """Massimo e minimo degli ULTIMI n giorni, barra corrente esclusa."""
    return (df["massimo"].rolling(n, min_periods=n).max().shift(1),
            df["minimo"].rolling(n, min_periods=n).min().shift(1))
