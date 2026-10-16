# Istruzioni per Claude Code / Codex

Banco di prova per strategie quantitative. Python puro, nomi in italiano.
Leggi prima LEGGIMI.md: contiene i risultati misurati, che sono il punto.

## Regole non negoziabili
- Nessun collegamento a broker. `carta.py` resta l'unico esecutore e un test
  verifica che non contenga codice di rete.
- Causalità: la barra t decide, la barra t+1 esegue. Lo sfasamento lo applica
  `backtest.esegui`, mai una funzione di segnale.
- Ogni strategia nuova: test anti-lookahead + walk-forward + permutazione.
- Il verdetto resta a tre condizioni (p, rumore da varianti, compra&tieni).
  Non ammorbidirlo per far sembrare buona una strategia.
- Test rossi prima del codice.

## Lavori, in ordine
1. Portafoglio: più strumenti insieme, pesi normalizzati, correlazione fra le
   gambe, rotazione totale sotto controllo.
2. Costi espliciti: finanziamento della leva, dividendi, bollo.
3. Una strategia che usi un dato diverso dal prezzo. È l'unico posto dove può
   esistere un edge, e va misurata con lo stesso metro.
4. `misura` su una lista di strumenti letta da file, con esecuzione parallela.
5. Loop di carta vero: un'esecuzione al giorno che appende al registro, più un
   comando che legge il registro e stampa le statistiche realizzate.

## Comandi
```
pytest test -q
python -m bot.cli misura --simboli SPY QQQ --permutazioni 300
```

## Il servizio sul server (Hetzner)

```
bot/avvisi.py      Telegram. Token SOLO da variabile d'ambiente, mai nel codice
bot/giro.py        giro giornaliero: idempotente per barra, stato atomico,
                   avvisa solo quando la posizione cambia
bot/__main__.py    python -m bot giro | riassunto | prova-telegram
deploy/            systemd service+timer, installa.sh idempotente, guida
```

Regole aggiuntive per chi tocca questa parte:

- Nessun segreto nel repository. `/etc/bot.env` (600, root) è l'unico posto.
  C'è un test che cerca token letterali nel sorgente: non aggirarlo.
- `giro()` deve restare idempotente per barra: due esecuzioni lo stesso giorno
  non devono produrre due righe nel diario.
- `installa.sh` non deve MAI toccare `dati/`: lì c'è il registro delle decisioni,
  che è l'unica cosa non ricostruibile.
- Il bot avvisa sui cambi, non ogni giorno. Un bot che scrive sempre viene
  silenziato, e allora non serve.
