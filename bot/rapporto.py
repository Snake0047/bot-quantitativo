"""Rapporto HTML autoconsistente. Nessuna rete, nessuna libreria."""
from __future__ import annotations

import html
import json
from pathlib import Path

import numpy as np
import pandas as pd

L = {"sup": "#fcfcfb", "pagina": "#f9f9f7", "ink": "#0b0b0b", "ink2": "#52514e",
     "muto": "#898781", "griglia": "#e1e0d9", "asse": "#c3c2b7",
     "s1": "#2a78d6", "s2": "#eb6834", "crit": "#d03b3b", "bordo": "rgba(11,11,11,.10)"}
D = {"sup": "#1a1a19", "pagina": "#0d0d0d", "ink": "#f0efec", "ink2": "#c3c2b7",
     "muto": "#898781", "griglia": "#2c2c2a", "asse": "#383835",
     "s1": "#3987e5", "s2": "#d95926", "crit": "#d03b3b", "bordo": "rgba(255,255,255,.10)"}


def _vars(d: dict) -> str:
    return "".join(f"--{k}:{v};" for k, v in d.items())


def _pct(x) -> str:
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x*100:+.1f}%"


def _n(x, c=2) -> str:
    return "—" if x is None or (isinstance(x, float) and np.isnan(x)) else f"{x:+.{c}f}"


def _campiona(s: pd.Series, n: int = 600) -> pd.Series:
    return s if len(s) <= n else s.iloc[:: max(1, len(s) // n)]


def _linee(serie: dict[str, pd.Series], alt=190, log=True) -> str:
    """Grafico a linee. Due serie al massimo, etichettate direttamente."""
    serie = {k: _campiona(v.dropna()) for k, v in serie.items() if len(v.dropna()) > 1}
    if not serie:
        return "<p class='vuoto'>nessun dato</p>"
    larg, ml, mr, mt, mb = 920, 52, 96, 14, 26
    tutti = pd.concat(serie.values())
    lo, hi = float(tutti.min()), float(tutti.max())
    f = (lambda v: np.log(max(v, 1e-9))) if log else (lambda v: v)
    flo, fhi = f(lo), f(hi)
    if fhi - flo < 1e-9:
        fhi = flo + 1e-9
    idx = sorted({d for s in serie.values() for d in s.index})
    t0, t1 = idx[0].value, idx[-1].value

    def X(d): return ml + (d.value - t0) / max(t1 - t0, 1) * (larg - ml - mr)
    def Y(v): return mt + (fhi - f(v)) / (fhi - flo) * (alt - mt - mb)

    out = [f'<svg viewBox="0 0 {larg} {alt}" role="img" class="g">']
    for q in (0, .25, .5, .75, 1):
        y = mt + q * (alt - mt - mb)
        val = np.exp(fhi - q * (fhi - flo)) if log else fhi - q * (fhi - flo)
        out.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{larg-mr}" y2="{y:.1f}" class="gr"/>')
        out.append(f'<text x="{ml-8}" y="{y+3.5:.1f}" class="tk" text-anchor="end">{val:.2f}×</text>')
    for n_, (nome, s) in enumerate(serie.items()):
        col = f"var(--s{n_+1})"
        d = " ".join(f"{'M' if i == 0 else 'L'}{X(x):.1f},{Y(v):.1f}"
                     for i, (x, v) in enumerate(s.items()))
        out.append(f'<path d="{d}" fill="none" stroke="{col}" stroke-width="2" '
                   f'stroke-linejoin="round" stroke-linecap="round"/>')
        ux, uv = s.index[-1], float(s.iloc[-1])
        out.append(f'<circle cx="{X(ux):.1f}" cy="{Y(uv):.1f}" r="4" fill="{col}"/>')
        out.append(f'<text x="{X(ux)+9:.1f}" y="{Y(uv)+4:.1f}" class="et" fill="{col}">'
                   f'{html.escape(nome)} {uv:.1f}×</text>')
    for d in (idx[0], idx[len(idx)//2], idx[-1]):
        out.append(f'<text x="{X(d):.1f}" y="{alt-6}" class="tk" text-anchor="middle">{d.year}</text>')
    out.append(f'<line x1="{ml}" y1="{alt-mb}" x2="{larg-mr}" y2="{alt-mb}" class="ax"/>')
    out.append("</svg>")
    return "".join(out)


def _drawdown(eq: pd.Series, alt=120) -> str:
    serie = (eq / eq.cummax() - 1).dropna()
    if len(serie) > 600:
        g = np.arange(len(serie)) // max(1, len(serie) // 600)
        dd = serie.groupby(g).min()
        dd.index = serie.index[pd.Series(np.arange(len(serie))).groupby(g).min().values]
    else:
        dd = serie
    if len(dd) < 2:
        return ""
    larg, ml, mr, mt, mb = 920, 52, 96, 12, 24
    peggio = float(dd.min()) or -1e-9
    t0, t1 = dd.index[0].value, dd.index[-1].value
    def X(d): return ml + (d.value - t0) / max(t1 - t0, 1) * (larg - ml - mr)
    def Y(v): return mt + (v / peggio) * (alt - mt - mb)
    pts = " ".join(f"{X(x):.1f},{Y(v):.1f}" for x, v in dd.items())
    out = [f'<svg viewBox="0 0 {larg} {alt}" role="img" class="g">',
           f'<polygon points="{ml},{mt} {pts} {X(dd.index[-1]):.1f},{mt}" '
           f'fill="var(--crit)" fill-opacity="0.16"/>',
           f'<polyline points="{pts}" fill="none" stroke="var(--crit)" stroke-width="2"/>',
           f'<line x1="{ml}" y1="{mt}" x2="{larg-mr}" y2="{mt}" class="ax"/>',
           f'<text x="{ml-8}" y="{mt+4}" class="tk" text-anchor="end">0%</text>',
           f'<text x="{ml-8}" y="{alt-mb+4}" class="tk" text-anchor="end">{peggio*100:.0f}%</text>',
           "</svg>"]
    return "".join(out)


CSS = """
*{box-sizing:border-box}
body{margin:0;background:var(--pagina);color:var(--ink);
 font:15px/1.55 system-ui,-apple-system,"Segoe UI",sans-serif;padding:24px 16px 64px}
.w{max-width:960px;margin:0 auto}
h1{font-size:26px;margin:0 0 4px;letter-spacing:-.02em}
h2{font-size:17px;margin:34px 0 10px;letter-spacing:-.01em}
h3{font-size:14px;margin:18px 0 6px;color:var(--ink2);font-weight:600}
.sot{color:var(--ink2);margin:0 0 22px;font-size:14px}
.c{background:var(--sup);border:1px solid var(--bordo);border-radius:12px;padding:16px 18px;margin:12px 0}
.g{width:100%;height:auto;display:block;overflow:visible}
.gr{stroke:var(--griglia);stroke-width:1}
.ax{stroke:var(--asse);stroke-width:1}
.tk{fill:var(--muto);font-size:10px;font-variant-numeric:tabular-nums}
.et{font-size:11px;font-weight:600}
table{border-collapse:collapse;width:100%;font-size:13.5px;
 font-variant-numeric:tabular-nums;margin-top:6px}
th,td{text-align:right;padding:7px 8px;border-bottom:1px solid var(--bordo);white-space:nowrap}
th:first-child,td:first-child{text-align:left;font-variant-numeric:normal}
th{color:var(--ink2);font-weight:600;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.vd{display:inline-flex;align-items:center;gap:6px;font-weight:600}
.pal{width:9px;height:9px;border-radius:2px;display:inline-block}
.no{color:var(--crit)} .si{color:#0ca30c} .nd{color:var(--ink2)}
.nota{font-size:13px;color:var(--ink2);margin:8px 0 0}
.vuoto{color:var(--muto);font-size:13px}
.tab{overflow-x:auto}
@media(max-width:640px){body{padding:16px 12px 48px}h1{font-size:21px}}
"""


def genera(risultati: list[dict], percorso: str | Path,
           titolo: str = "Bot — misura su dati reali") -> Path:
    p = Path(percorso)
    b = []
    b.append(f"<!doctype html><html lang='it'><meta charset='utf-8'>"
             f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
             f"<title>{html.escape(titolo)}</title><style>:root{{{_vars(L)}color-scheme:light}}"
             f"@media(prefers-color-scheme:dark){{:root:not([data-theme='light'])"
             f"{{{_vars(D)}color-scheme:dark}}}}"
             f":root[data-theme='dark']{{{_vars(D)}color-scheme:dark}}{CSS}</style>"
             f"<body><div class='w'><h1>{html.escape(titolo)}</h1>")
    b.append("<p class='sot'>Ogni cifra è al netto di commissioni e slippage. "
             "La curva fuori campione è l'unica a cui credere: i parametri di ogni "
             "finestra sono scelti solo sul passato.</p>")

    b.append("<h2>Sintesi</h2><div class='c tab'><table><thead><tr>"
             "<th>Strumento</th><th>Strategia</th><th>Sharpe OOS</th><th>Rumore</th>"
             "<th>p</th><th>CAGR OOS</th><th>maxDD</th><th>Compra&amp;tieni</th>"
             "<th>Verdetto</th></tr></thead><tbody>")
    for r in risultati:
        if r["p"] >= 0.05 or r["sharpe_oos"] <= r["sharpe_rumore_varianti"]:
            verdetto, classe = "rumore", "no"
        elif r["sharpe_oos"] <= r["sharpe_bh"]:
            verdetto, classe = "segnale, non batte b&amp;t", "nd"
        else:
            verdetto, classe = "batte b&amp;t", "si"
        b.append(f"<tr><td>{html.escape(r['simbolo'])}</td>"
                 f"<td>{html.escape(r['strategia'])}</td>"
                 f"<td>{_n(r['sharpe_oos'])}</td><td>{_n(r['rumore'])}</td>"
                 f"<td>{r['p']:.3f}</td><td>{_pct(r['cagr_oos'])}</td>"
                 f"<td>{_pct(r['dd_oos'])}</td><td>{_n(r['sharpe_bh'])}</td>"
                 f"<td class='{classe}'>{verdetto}</td></tr>")
    b.append("</tbody></table></div>")

    for r in risultati:
        b.append(f"<h2>{html.escape(r['simbolo'])} · {html.escape(r['strategia'])}</h2>")
        b.append("<div class='c'>")
        b.append("<h3>Equity fuori campione, scala logaritmica</h3>")
        b.append(f"<span class='vd'><span class='pal' style='background:var(--s1)'></span>"
                 f"strategia</span> &nbsp; "
                 f"<span class='vd'><span class='pal' style='background:var(--s2)'></span>"
                 f"compra e tieni</span>")
        b.append(_linee({"strategia": r["eq_oos"], "compra e tieni": r["eq_bh"]}))
        b.append("<h3>Drawdown della strategia</h3>")
        b.append(_drawdown(r["eq_oos"]))
        b.append("<h3>Finestre fuori campione</h3><div class='tab'><table><thead><tr>"
                 "<th>fino a</th><th>parametri scelti</th><th>Sharpe in campione</th>"
                 "<th>Sharpe fuori</th></tr></thead><tbody>")
        for f_ in r["finestre"]:
            b.append(f"<tr><td>{f_['fine']}</td>"
                     f"<td style='text-align:left'>{html.escape(json.dumps(f_['par'], ensure_ascii=False))}</td>"
                     f"<td>{_n(f_['is'])}</td><td>{_n(f_['oos'])}</td></tr>")
        b.append("</tbody></table></div>")
        b.append(f"<p class='nota'>Permutazione: Sharpe vero {_n(r['sharpe_pieno'])}, "
                 f"rumore medio {_n(r['rumore'])}, p = {r['p']:.3f} su {r['n_perm']} mondi "
                 f"casuali. Sharpe atteso dal solo numero di varianti provate "
                 f"({r['n_varianti']}): {_n(r['sharpe_rumore_varianti'])}.</p>")
        b.append("</div>")

    b.append("<h2>Come leggere</h2><div class='c'><p class='nota'>"
             "<b>p</b> è la quota di mondi casuali in cui la stessa strategia fa meglio "
             "che nel mondo vero. p alto significa che non sta leggendo nulla. "
             "<b>Rumore</b> è lo Sharpe medio su quei mondi. "
             "Una strategia vale qualcosa solo se batte il compra e tieni <i>e</i> "
             "ha p basso <i>e</i> il suo Sharpe supera quello che il numero di varianti "
             "provate produrrebbe da solo. Tre condizioni, non una."
             "</p></div></div></body></html>")
    p.write_text("".join(b), encoding="utf-8")
    return p
