"""Misura su dati reali gratuiti: il segnale a regole vale qualcosa?"""
import sys, numpy as np, pandas as pd, yfinance as yf

COSTO = 0.001   # commissione+slippage per lato

def serie(sym, start="2005-01-01"):
    d = yf.download(sym, start=start, auto_adjust=True, progress=False)
    if isinstance(d.columns, pd.MultiIndex): d.columns = d.columns.get_level_values(0)
    return d["Close"].dropna()

def segnale(px, veloce=20, lenta=100):
    mv, ml = px.rolling(veloce).mean(), px.rolling(lenta).mean()
    return ((mv > ml) & (px > ml)).astype(float).fillna(0.0)

def esegui(px, pos, costo=COSTO):
    pos = pos.shift(1).fillna(0.0)
    r = px.pct_change().fillna(0.0)
    scambio = pos.diff().abs().fillna(pos.abs())
    netto = pos*r - scambio*costo
    eq = (1+netto).cumprod()
    anni = len(netto)/252
    sh = netto.mean()/netto.std()*np.sqrt(252) if netto.std()>0 else 0.0
    dd = float((eq/eq.cummax()-1).min())
    cagr = float(eq.iloc[-1])**(1/anni)-1
    return dict(sharpe=float(sh), cagr=cagr, dd=dd, dentro=float((pos.abs()>0).mean()),
                finale=float(eq.iloc[-1]))

def bh(px):
    r = px.pct_change().fillna(0.0); eq=(1+r).cumprod(); anni=len(r)/252
    return dict(sharpe=float(r.mean()/r.std()*np.sqrt(252)), cagr=float(eq.iloc[-1])**(1/anni)-1,
                dd=float((eq/eq.cummax()-1).min()), dentro=1.0, finale=float(eq.iloc[-1]))

def permutazione(px, n=500, seme=1):
    vero = esegui(px, segnale(px))["sharpe"]
    r = np.random.default_rng(seme); rend = px.pct_change().dropna().values
    out=[]
    for _ in range(n):
        p = pd.Series(np.r_[px.iloc[0], px.iloc[0]*np.cumprod(1+r.permutation(rend))], index=px.index[:len(rend)+1])
        out.append(esegui(p, segnale(p))["sharpe"])
    out=np.asarray(out)
    return vero, float(out.mean()), float(np.percentile(out,95)), float((out>=vero).mean())

for sym in sys.argv[1:] or ["SPY"]:
    px = serie(sym)
    s, b = esegui(px, segnale(px)), bh(px)
    v, m, p95, p = permutazione(px, 400)
    print(f"\n=== {sym}  ({px.index[0].date()} -> {px.index[-1].date()}, {len(px)} barre) ===")
    print(f"  strategia   sharpe {s['sharpe']:+.2f}  cagr {s['cagr']*100:+.1f}%  maxDD {s['dd']*100:.1f}%  dentro {s['dentro']*100:.0f}%  x{s['finale']:.1f}")
    print(f"  compra&tieni sharpe {b['sharpe']:+.2f}  cagr {b['cagr']*100:+.1f}%  maxDD {b['dd']*100:.1f}%  dentro 100%  x{b['finale']:.1f}")
    print(f"  permutazione: vero {v:+.2f} | rumore medio {m:+.2f} | rumore p95 {p95:+.2f} | p = {p:.3f}")
