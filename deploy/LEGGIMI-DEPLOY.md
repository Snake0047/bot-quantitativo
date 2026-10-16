# Mettere il bot su Hetzner

Tempo reale: 20-30 minuti la prima volta. Costo: ~4-5 €/mese.

## 0. Il bot Telegram (3 minuti, dal telefono)

1. Su Telegram cerca **@BotFather** → `/newbot` → nome e username.
2. Ti dà un token tipo `8123456789:AAH...`. **Quel token è una password.**
   Non va su GitHub, non va in una chat, non lo mandi a me.
3. Scrivi un messaggio qualsiasi al tuo bot appena creato.
4. Apri nel browser `https://api.telegram.org/bot<IL_TUO_TOKEN>/getUpdates`
   e copia il numero in `"chat":{"id":...}`. Quello è il chat id.

## 1. Il server (5 minuti)

Hetzner Cloud → nuovo progetto → **Add Server**:

- Location: Falkenstein o Norimberga
- Image: **Ubuntu 24.04**
- Type: **CX22** (shared vCPU, ~4,5 €/mese) — più che sufficiente
- SSH key: **aggiungi la tua chiave pubblica**, non usare la password
- Nome: `bot`

Se non hai una chiave: `ssh-keygen -t ed25519` sul tuo computer, poi incolli
il contenuto di `~/.ssh/id_ed25519.pub`.

## 2. Caricare e installare (10 minuti)

Dal tuo computer, nella cartella del progetto:

```bash
rsync -av --exclude dati --exclude .venv --exclude __pycache__ \
      ./ root@<IP_DEL_SERVER>:/root/bot-sorgente/
ssh root@<IP_DEL_SERVER> 'bash /root/bot-sorgente/deploy/installa.sh /root/bot-sorgente'
```

Poi, sul server:

```bash
nano /etc/bot.env          # incolli token e chat id QUI, e solo qui
sudo -u bot /opt/bot/.venv/bin/python -m bot prova-telegram
```

Se ti arriva il messaggio su Telegram, è finita.

## 3. Cosa fa da solo

| quando | cosa |
|---|---|
| lun-ven 23:30 | scarica, decide, registra. Scrive su Telegram **solo se la posizione cambia** |
| domenica 19:00 | riassunto della settimana |

Il ritardo casuale di 10 minuti nel timer evita di bussare a yfinance
allo stesso secondo di tutti gli altri.

## 4. Comandi utili

```bash
systemctl list-timers 'bot*'              # quando parte la prossima volta
journalctl -u bot.service -n 50           # cosa ha fatto l'ultima volta
systemctl start bot.service               # fallo partire adesso
sudo -u bot /opt/bot/.venv/bin/python -m bot riassunto --giorni 30
cat /opt/bot/dati/diario.jsonl | wc -l    # quante decisioni hai raccolto
```

## 5. Sicurezza — cosa fa già l'installatore

- gira come utente `bot`, non root, senza shell di login
- `/etc/bot.env` a 600, proprietario root: l'utente `bot` lo legge solo via systemd
- systemd: filesystem in sola lettura tranne `dati/`, niente privilegi nuovi,
  memoria limitata a 512 MB
- `ufw`: entra solo SSH, esce tutto

Cosa devi fare tu: **disattivare il login SSH con password**
(`PasswordAuthentication no` in `/etc/ssh/sshd_config`, poi
`systemctl restart ssh`). Con la chiave già configurata non perdi l'accesso.

## 6. Aggiornare

Rilanci gli stessi due comandi del punto 2. `installa.sh` è idempotente e
**non tocca mai `dati/`**: il registro delle decisioni resta.

## 7. Se vuoi spegnere tutto

```bash
systemctl disable --now bot.timer bot-riassunto.timer
```

E su Hetzner cancelli il server. Il costo si ferma lì.

---

**Il bot non invia nessun ordine a nessun broker.** Scrive su un file e su
Telegram. Non c'è codice di rete in `carta.py` e un test lo verifica.
