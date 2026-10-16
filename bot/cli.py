"""Punto d'ingresso.

  python -m bot.cli misura --simboli SPY QQQ GLD --strategie trend breakout
  python -m bot.cli carta  --simbolo SPY
"""
from __future__ import annotations

import argparse
import json

import pandas as pd

from . import dati, strategie
from .backtest import Costi, compra_e_tieni, esegui
from .carta import Conto
from .rapporto import genera
from .rischio import Guardia
from .validazione import (deflaziona, permutazione, scegli, sharpe_da_rumore,
                          walk_forward)

PER_NOME = {s.nome: s for s in strategie.TUTTE}


def cmd_misura(a) -> None:
    costi = Costi(a.commissione, a.slippage)
    righe, stampa = [], []
    for sim in a.simboli:
        df = dati.carica(sim, a.inizio, riusa=not a.aggiorna)
        eq_bh, e_bh = compra_e_tieni(df)
        for nome in a.strategie:
            s = PER_NOME[nome]
            eq, fin, e = walk_forward(s, df, a.barre_is, a.barre_oos, costi)
            if not fin:
                continue
            par_pieno, _ = scegli(s, df, costi)
            perm = permutazione(s, df, par_pieno, a.permutazioni, costi=costi)
            inizio_oos = eq.index[0]
            righe.append({
                "simbolo": sim, "strategia": nome,
                "eq_oos": eq,
                "eq_bh": (eq_bh.loc[inizio_oos:] / eq_bh.loc[inizio_oos]),
                "sharpe_oos": e.sharpe, "cagr_oos": e.cagr, "dd_oos": e.max_drawdown,
                "sharpe_bh": e_bh.sharpe,
                "sharpe_pieno": perm["sharpe_vero"], "rumore": perm["rumore_medio"],
                "p": perm["p"], "n_perm": perm["n"],
                "n_varianti": s.n_combinazioni,
                "sharpe_rumore_varianti": sharpe_da_rumore(s.n_combinazioni, a.barre_is),
                "finestre": [{"fine": str(f.fine.date()), "par": f.parametri,
                              "is": f.sharpe_is, "oos": f.sharpe_oos} for f in fin],
            })
            stampa.append(f"{sim:>5} {nome:<14} sharpe_oos {e.sharpe:+.2f} "
                          f"cagr {e.cagr*100:+5.1f}% dd {e.max_drawdown*100:6.1f}% "
                          f"| b&h {e_bh.sharpe:+.2f} | p {perm['p']:.3f}")
    print("\n".join(stampa))
    if righe:
        print("\nrapporto →", genera(righe, a.rapporto))


def cmd_carta(a) -> None:
    df = dati.carica(a.simbolo, a.inizio, riusa=not a.aggiorna)
    s = PER_NOME[a.strategie[0]]
    par, _ = scegli(s, df.iloc[:-a.barre_oos], Costi(a.commissione, a.slippage))
    pos = strategie.dimensiona(s.segnale(df, par), df)
    peso = Guardia().filtra(float(pos.iloc[-1]))
    conto = Conto()
    riga = conto.porta_a(peso, float(df["chiusura"].iloc[-1]),
                         nota=f"{s.nome} {par}")
    print(json.dumps({"data": str(df.index[-1].date()), "parametri": par,
                      "peso": round(peso, 4), "ordine": riga,
                      "conto": conto.stato()}, indent=2, ensure_ascii=False))


def principale() -> None:
    comuni = argparse.ArgumentParser(add_help=False)
    comuni.add_argument("--simboli", nargs="+", default=["SPY"])
    comuni.add_argument("--simbolo", default="SPY")
    comuni.add_argument("--strategie", nargs="+", default=list(PER_NOME),
                        choices=list(PER_NOME))
    comuni.add_argument("--inizio", default="2005-01-01")
    comuni.add_argument("--aggiorna", action="store_true",
                        help="riscarica invece di usare la cache")
    comuni.add_argument("--commissione", type=float, default=0.0005)
    comuni.add_argument("--slippage", type=float, default=0.0005)
    comuni.add_argument("--barre-is", type=int, default=1008)
    comuni.add_argument("--barre-oos", type=int, default=126)
    comuni.add_argument("--permutazioni", type=int, default=300)
    comuni.add_argument("--rapporto", default="rapporto.html")

    p = argparse.ArgumentParser(prog="bot", parents=[comuni])
    s = p.add_subparsers(dest="cmd", required=True)
    s.add_parser("misura", parents=[comuni]).set_defaults(fn=cmd_misura)
    s.add_parser("carta", parents=[comuni]).set_defaults(fn=cmd_carta)
    a = p.parse_args()
    a.fn(a)


if __name__ == "__main__":
    principale()
