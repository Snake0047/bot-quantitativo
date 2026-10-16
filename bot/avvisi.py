"""Avvisi su Telegram.

Il token e il chat id arrivano SOLO da variabili d'ambiente. Non stanno nel
codice, non finiscono nei log, non passano da una chat. Se mancano, il modulo
non esplode: stampa e basta, così il giro funziona anche senza Telegram.
"""
from __future__ import annotations

import json
import os
import urllib.error
import urllib.parse
import urllib.request

API = "https://api.telegram.org/bot{token}/sendMessage"
LIMITE = 4000   # Telegram taglia a 4096


def configurato() -> bool:
    return bool(os.getenv("TELEGRAM_TOKEN") and os.getenv("TELEGRAM_CHAT_ID"))


def _tronca(testo: str) -> str:
    return testo if len(testo) <= LIMITE else testo[: LIMITE - 3] + "..."


def manda(testo: str, silenzioso: bool = False) -> bool:
    """True se Telegram ha accettato il messaggio. Non solleva mai."""
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        print(f"[telegram non configurato]\n{testo}")
        return False
    dati = urllib.parse.urlencode({
        "chat_id": chat,
        "text": _tronca(testo),
        "parse_mode": "HTML",
        "disable_notification": silenzioso,
        "disable_web_page_preview": True,
    }).encode()
    try:
        with urllib.request.urlopen(API.format(token=token), dati, timeout=20) as r:
            return json.load(r).get("ok", False)
    except (urllib.error.URLError, TimeoutError, ValueError) as e:
        # mai il token nel messaggio d'errore
        print(f"[telegram: invio fallito: {type(e).__name__}]")
        return False


def prova() -> bool:
    return manda("<b>bot</b> — collegamento riuscito.")
