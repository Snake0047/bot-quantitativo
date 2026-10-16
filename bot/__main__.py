"""python -m bot <comando> — ciò che gira sul server."""
from __future__ import annotations

import argparse

from . import avvisi, giro


def principale() -> None:
    p = argparse.ArgumentParser(prog="bot")
    s = p.add_subparsers(dest="cmd", required=True)

    g = s.add_parser("giro", help="un'esecuzione giornaliera")
    g.add_argument("--simboli", nargs="+", default=["SPY", "QQQ"])
    g.add_argument("--strategia", default="trend")
    g.add_argument("--forza", action="store_true", help="rifai anche se già fatto oggi")
    g.add_argument("--sempre", action="store_true", help="avvisa anche quando non cambia niente")

    r = s.add_parser("riassunto", help="cosa è successo di recente")
    r.add_argument("--giorni", type=int, default=7)

    s.add_parser("prova-telegram", help="verifica il collegamento")

    a = p.parse_args()
    if a.cmd == "giro":
        fatte = giro.esegui(a.simboli, a.strategia, a.forza, a.sempre)
        for d in fatte:
            print(f"{d.simbolo} {d.motivo} {d.peso_prima:.0%}→{d.peso:.0%}")
        if not fatte:
            print("niente da fare: barra già elaborata")
    elif a.cmd == "riassunto":
        t = giro.riassunto(a.giorni)
        print(t.replace("<b>", "").replace("</b>", ""))
        avvisi.manda(t)
    else:
        print("ok" if avvisi.prova() else "fallito (token/chat id assenti o errati)")


if __name__ == "__main__":
    principale()
