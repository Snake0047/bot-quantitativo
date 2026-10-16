"""Serie storiche OHLCV da fonti gratuite, con cache su disco."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd

CARTELLA = Path(__file__).resolve().parent.parent / "dati"
COLONNE = ("apertura", "massimo", "minimo", "chiusura", "volume")


class DatiInsufficienti(ValueError):
    pass


def _normalizza(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    df.columns = [str(c).strip().lower() for c in df.columns]
    rinomina = {"open": "apertura", "high": "massimo", "low": "minimo",
                "close": "chiusura", "adj close": "chiusura", "volume": "volume"}
    df = df.rename(columns={k: v for k, v in rinomina.items() if k in df.columns})
    mancanti = [c for c in COLONNE if c not in df.columns]
    if mancanti:
        raise DatiInsufficienti(f"colonne mancanti: {mancanti}")
    df = df[list(COLONNE)].astype(float)
    df.index = pd.to_datetime(df.index, utc=True)
    df = df[~df.index.duplicated(keep="last")].sort_index().dropna()
    if (df["massimo"] < df["minimo"]).any():
        raise DatiInsufficienti("massimo < minimo: dati corrotti")
    if len(df) < 300:
        raise DatiInsufficienti(f"solo {len(df)} barre: troppo poche")
    return df


def da_csv(percorso: str | Path) -> pd.DataFrame:
    return _normalizza(pd.read_csv(percorso, index_col=0))


def scarica(simbolo: str, inizio: str = "2005-01-01") -> pd.DataFrame:
    import yfinance as yf
    df = yf.download(simbolo, start=inizio, auto_adjust=True, progress=False)
    if df.empty:
        raise DatiInsufficienti(f"nessun dato per {simbolo}")
    return _normalizza(df)


def carica(simbolo: str, inizio: str = "2005-01-01", riusa: bool = True) -> pd.DataFrame:
    CARTELLA.mkdir(parents=True, exist_ok=True)
    f = CARTELLA / f"{simbolo}.csv"
    if riusa and f.exists():
        return da_csv(f)
    df = scarica(simbolo, inizio)
    df.to_csv(f)
    return df


@dataclass
class Sintetico:
    """Serie finta a seme fisso: serve ai test, non alle conclusioni."""
    giorni: int = 1500
    deriva: float = 0.0003
    vol: float = 0.012
    seme: int = 7

    def serie(self) -> pd.DataFrame:
        r = np.random.default_rng(self.seme)
        px = 100 * np.exp(np.cumsum(r.normal(self.deriva, self.vol, self.giorni)))
        idx = pd.date_range("2018-01-01", periods=self.giorni, freq="D", tz="UTC")
        alto = px * (1 + np.abs(r.normal(0, self.vol / 2, self.giorni)))
        basso = px * (1 - np.abs(r.normal(0, self.vol / 2, self.giorni)))
        return _normalizza(pd.DataFrame({
            "apertura": np.r_[px[0], px[:-1]],
            "massimo": np.maximum(alto, px),
            "minimo": np.minimum(basso, px),
            "chiusura": px,
            "volume": r.lognormal(10, 0.4, self.giorni),
        }, index=idx))
