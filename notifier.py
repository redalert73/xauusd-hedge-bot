# ==========================================
# NOTIFICHE - SOLO TELEGRAM
# ==========================================

import os
import requests

TIMEOUT = 10


def _creds():
    return os.getenv("TELEGRAM_BOT_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")


def send_notification(message: str) -> bool:
    """Invia un messaggio Telegram in testo semplice. True solo se Telegram conferma."""
    token, chat_id = _creds()
    if not token or not chat_id:
        print("Telegram non configurato (TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID).")
        return False
    try:
        r = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": message},
            timeout=TIMEOUT,
        )
        if not r.ok:
            # Il corpo della risposta Telegram non contiene il token.
            print(f"Telegram ha rifiutato il messaggio: HTTP {r.status_code} {r.text[:200]}")
            return False
        return True
    except requests.RequestException as e:
        # Non stampo l'eccezione completa: l'URL contiene il token.
        print(f"Errore di rete verso Telegram: {type(e).__name__}")
        return False


def fetch_commands(offset: int):
    """Legge i comandi nuovi inviati al bot dal TUO chat id.

    Ritorna (lista_comandi, nuovo_offset). I comandi arrivano in minuscolo,
    es. "/stop", "/riprendi", "/stato". Messaggi di altre chat vengono ignorati.
    """
    token, chat_id = _creds()
    if not token or not chat_id:
        return [], offset
    try:
        r = requests.get(
            f"https://api.telegram.org/bot{token}/getUpdates",
            params={"offset": offset, "timeout": 0},
            timeout=TIMEOUT,
        )
        if not r.ok:
            return [], offset
        data = r.json()
    except (requests.RequestException, ValueError):
        return [], offset

    commands, new_offset = [], offset
    for upd in data.get("result", []):
        new_offset = max(new_offset, upd["update_id"] + 1)
        msg = upd.get("message") or {}
        if str((msg.get("chat") or {}).get("id")) != str(chat_id):
            continue
        text = (msg.get("text") or "").strip().lower()
        if text.startswith("/"):
            commands.append(text.split()[0].split("@")[0])
    return commands, new_offset
