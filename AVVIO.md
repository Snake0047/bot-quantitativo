# Avvio — tutto gratis, 20 minuti

Nessun server, nessun costo. GitHub Actions esegue il giro ogni sera feriale e
riscrive il diario nel repository, così la memoria non si perde.

## 1 · Il bot Telegram (3 min, dal telefono)

1. Telegram → **@BotFather** → `/newbot` → nome e username.
2. Ti dà un token tipo `8123456789:AAH...`. **È una password**: non va nel
   codice, non va in una chat, non lo mandi a nessuno.
3. Scrivi un messaggio qualsiasi al bot appena creato.
4. Apri `https://api.telegram.org/bot<IL_TUO_TOKEN>/getUpdates` e copia il
   numero in `"chat":{"id":...}` → è il tuo chat id.

## 2 · Il repository (5 min)

```bash
cd bot
git init -b main
git add .
git commit -m "primo commit: banco di prova per strategie quantitative"
gh repo create bot-quantitativo --public --source=. --push
```

Senza `gh`: crei il repo a mano su github.com e poi
`git remote add origin <url> && git push -u origin main`.

**Pubblico**, non privato: i minuti di Actions sono illimitati sui repo
pubblici, e questo repo è il tuo portfolio. Nel diario non c'è niente di
personale — sono decisioni su ETF, in carta.

## 3 · I due segreti (2 min)

GitHub → il tuo repo → **Settings → Secrets and variables → Actions →
New repository secret**. Due volte:

| nome | valore |
|---|---|
| `TELEGRAM_TOKEN` | il token di BotFather |
| `TELEGRAM_CHAT_ID` | il numero del punto 1.4 |

I secret non si rileggono più dopo il salvataggio e non compaiono nei log:
è il posto giusto dove metterli.

## 4 · La prova (2 min)

GitHub → **Actions** → *giro giornaliero* → **Run workflow**.

Se ti arriva il messaggio su Telegram, hai finito. Da lì in poi:

| quando | cosa |
|---|---|
| lun-ven, ~23:45 italiane | scarica, decide, scrive il diario. Avvisa **solo se la posizione cambia** |
| domenica sera | riassunto della settimana |
| a ogni push | i 37 test girano da soli |

## Tre cose da sapere

**Il cron di GitHub è in UTC e può ritardare** di qualche decina di minuti
sotto carico. Per un giro giornaliero non cambia niente.

**GitHub sospende i workflow programmati** nei repository fermi da 60 giorni.
Qui non succede: ogni giro fa un commit, e il commit è attività.

**Lo stato vive nel repository.** `dati/diario.jsonl` e `dati/stato.json`
vengono riscritti a ogni giro. Se li cancelli, il bot riparte da zero e perdi
il campione — che è l'unica cosa che non si ricostruisce.

## Se un giorno vuoi il server vero

In `deploy/` c'è il kit per Hetzner: systemd, timer, `installa.sh`
idempotente, hardening. Costa ~4,5 €/mese e non serve finché il giro è uno al
giorno. Resta lì per quando servirà.

## Il traguardo

**Gennaio.** Circa 60 decisioni registrate su dati veri, prese in anticipo e
mai ritoccate. A quel punto il diario si confronta con il backtest: se le
decisioni reali assomigliano alla simulazione, l'impianto è onesto. Se no,
c'è un errore e si trova.

Fino ad allora: **zero capitale**.
