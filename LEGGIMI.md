# bot — banco di prova per strategie quantitative

Non è un bot che fa soldi. È l'impianto che dice **se** una strategia ne fa,
prima di rischiare un euro — e che nella maggior parte dei casi risponde di no.

## Il risultato, prima di tutto il resto

Tre strategie classiche, tre strumenti, 2005 → 2026, walk-forward con i
parametri scelti solo sul passato, commissioni e slippage inclusi:

| strumento | strategia | Sharpe OOS | p | CAGR OOS | maxDD | compra&tieni | verdetto |
|---|---|---|---|---|---|---|---|
| SPY | trend | +0,65 | 0,005 | +6,4% | -21,8% | +0,64 | rumore |
| SPY | ritorno_media | +0,09 | 0,065 | +0,3% | -15,2% | +0,64 | rumore |
| SPY | breakout | +0,52 | 0,025 | +4,6% | -29,3% | +0,64 | rumore |
| QQQ | trend | +0,78 | 0,005 | +9,3% | -17,4% | +0,76 | batte b&t |
| QQQ | ritorno_media | +0,19 | 0,015 | +0,9% | -16,0% | +0,76 | rumore |
| QQQ | breakout | +0,79 | 0,100 | +8,8% | -16,6% | +0,76 | rumore |
| GLD | trend | +0,57 | 0,050 | +5,8% | -39,4% | +0,64 | rumore |
| GLD | ritorno_media | -0,44 | 0,140 | -1,4% | -28,1% | +0,64 | rumore |
| GLD | breakout | +0,63 | 0,105 | +6,1% | -29,2% | +0,64 | rumore |

Otto righe su nove dicono **rumore**, e la nona batte il comprare e tenere di
0,02 di Sharpe, cioè di niente.

Il p-value basso su diversi trend non è un errore: una struttura seriale nei
prezzi esiste davvero, e la permutazione la rileva. Ma la strategia la
converte in **meno drawdown**, non in più rendimento — -21,8% contro il -55%
del comprare e tenere su SPY, a parità di Sharpe e con un terzo del montante
finale. Il trend following sposta rischio; non crea rendimento.

Questo è il risultato onesto, ed è il motivo per cui l'impianto esiste.

## Le tre condizioni del verdetto

Una strategia è promossa solo se, insieme:

1. **p < 0,05** nel test di permutazione — non sta leggendo rumore;
2. **Sharpe OOS > Sharpe da rumore** dato il numero di varianti provate —
   con 9 combinazioni su 4 anni il caso produce da solo circa 0,76, quindi uno
   Sharpe di 0,65 vale meno di zero;
3. **Sharpe OOS > compra e tieni** — altrimenti la cosa più intelligente è
   comprare e non fare niente.

La maggior parte dei backtest che circolano supera zero condizioni su tre e
mostra una curva in salita.

## Struttura

```
dati.py         serie OHLCV gratuite (yfinance), cache su disco, serie sintetica per i test
indicatori.py   ATR, RSI, z-score, Donchian, volatilità — tutti causali
strategie.py    Strategia = griglia di parametri + funzione segnale. Tre implementazioni
backtest.py     l'UNICO punto in cui la posizione viene sfasata di una barra
validazione.py  walk-forward, permutazione, Sharpe deflazionato
rischio.py      tetti duri: leva, perdita giornaliera, drawdown-stop
carta.py        conto di carta, registro jsonl. Nessuna rete, verificato da un test
rapporto.py     rapporto HTML autoconsistente, chiaro e scuro
cli.py          misura | carta
```

## Uso

```bash
pip install -r requisiti-dev.txt
python -m bot.cli misura --simboli SPY QQQ GLD --permutazioni 300
python -m bot.cli carta  --simbolo SPY
pytest test -q
```

`misura` scrive `rapporto.html`: equity fuori campione, drawdown, parametri
scelti finestra per finestra.

## Le regole della casa

- La barra `t` decide, la barra `t+1` esegue. Lo sfasamento sta in un punto
  solo, così non si può dimenticare.
- Ogni strategia nuova arriva con un test anti-lookahead, un walk-forward e un
  test di permutazione. Senza i tre non entra.
- Nessun collegamento a un broker. `carta.py` è l'unico esecutore, e un test
  verifica che non contenga codice di rete.
- Test rossi prima del codice.

## Cosa manca

- portafoglio multi-strumento con pesi e correlazioni fra le gambe
- costi di finanziamento e dividendi espliciti
- strategie che usino dati diversi dal prezzo: è l'unico posto dove può
  esistere un edge che il prezzo da solo non ha

Non è consulenza finanziaria.
