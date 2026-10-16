#!/usr/bin/env bash
# =====================================================================
# Installa il bot su un server Debian/Ubuntu pulito (Hetzner CX22 va bene).
#
# USO, da root sul server:
#   curl -fsSL -o installa.sh <url>   # oppure scp dal tuo computer
#   bash installa.sh /percorso/al/bot
#
# Rilanciarlo è sicuro: aggiorna quello che c'è invece di rifare tutto.
# =====================================================================
set -euo pipefail

SORGENTE="${1:-$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)}"
DEST=/opt/bot
UTENTE=bot

verde()  { printf '\033[32m%s\033[0m\n' "$*"; }
giallo() { printf '\033[33m%s\033[0m\n' "$*"; }
rosso()  { printf '\033[31m%s\033[0m\n' "$*" >&2; }

[[ $EUID -eq 0 ]] || { rosso "Serve root. Usa: sudo bash installa.sh"; exit 1; }
[[ -f "$SORGENTE/bot/giro.py" ]] || { rosso "In $SORGENTE non c'è il bot."; exit 1; }

giallo "── 1/6 · pacchetti ─────────────────────────────────────────"
export DEBIAN_FRONTEND=noninteractive
apt-get update -qq
apt-get install -y -qq python3 python3-venv python3-pip ufw chrony >/dev/null
timedatectl set-timezone Europe/Rome || true

giallo "── 2/6 · utente senza privilegi ────────────────────────────"
id -u "$UTENTE" &>/dev/null || useradd --system --create-home --shell /usr/sbin/nologin "$UTENTE"

giallo "── 3/6 · codice ────────────────────────────────────────────"
mkdir -p "$DEST"
# i dati non si sovrascrivono mai: è il registro delle decisioni
rsync -a --delete --exclude 'dati/' --exclude '.git/' --exclude '__pycache__/' \
      --exclude '.venv/' "$SORGENTE/" "$DEST/"
mkdir -p "$DEST/dati"
chown -R "$UTENTE:$UTENTE" "$DEST"

giallo "── 4/6 · ambiente python ───────────────────────────────────"
[[ -d "$DEST/.venv" ]] || python3 -m venv "$DEST/.venv"
"$DEST/.venv/bin/pip" install -q --upgrade pip
"$DEST/.venv/bin/pip" install -q -r "$DEST/requisiti.txt"
chown -R "$UTENTE:$UTENTE" "$DEST/.venv"

giallo "── 5/6 · segreti ───────────────────────────────────────────"
if [[ ! -f /etc/bot.env ]]; then
  cp "$DEST/deploy/bot.env.esempio" /etc/bot.env
  giallo "   creato /etc/bot.env — RIEMPILO prima di continuare"
fi
chmod 600 /etc/bot.env
chown root:root /etc/bot.env
if ! grep -q '^TELEGRAM_TOKEN=.\+' /etc/bot.env; then
  giallo "   ATTENZIONE: TELEGRAM_TOKEN ancora vuoto in /etc/bot.env"
fi

giallo "── 6/6 · servizi e firewall ────────────────────────────────"
install -m 644 "$DEST"/deploy/bot*.service "$DEST"/deploy/bot*.timer /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now bot.timer bot-riassunto.timer >/dev/null

ufw --force default deny incoming >/dev/null
ufw --force default allow outgoing >/dev/null
ufw allow OpenSSH >/dev/null
ufw --force enable >/dev/null

cat <<FINE

$(verde "Installato.")

  codice    $DEST
  dati      $DEST/dati        (registro delle decisioni: non si cancella)
  segreti   /etc/bot.env      (600, root)
  timer     tutti i giorni feriali 23:30, riassunto la domenica alle 19:00

Verifica, in quest'ordine:

  nano /etc/bot.env                        # metti token e chat id, se non l'hai fatto
  sudo -u $UTENTE $DEST/.venv/bin/python -m bot prova-telegram
  sudo -u $UTENTE $DEST/.venv/bin/python -m bot giro --simboli SPY
  systemctl list-timers 'bot*'
  journalctl -u bot.service -n 40 --no-pager

Se "prova-telegram" scrive "ok" e ti arriva il messaggio, hai finito.

FINE
