# ==========================================
# CALENDARIO NOTIZIE - blocca i segnali intorno alle notizie forti
# ==========================================
# Fonte gratuita: calendario settimanale di Forex Factory (JSON). Viene scaricato poche volte al giorno
# e tenuto nello stato del bot. Il verso dell'effetto di una notizia NON e' prevedibile: il filtro
# evita tutte le notizie forti, non solo quelle "contrarie" al segnale.

from datetime import datetime, timedelta, timezone

import requests

import config

TIMEOUT = 10
RETRY_MIN = 30          # dopo un download fallito non riprovo prima di cosi'
VALID_HOURS = 24        # oltre questo tempo dall'ultimo download riuscito il calendario non e' affidabile


def _now_iso(now_utc):
    return now_utc.strftime("%Y-%m-%dT%H:%M:%S")


def _parse(ts):
    return datetime.strptime(ts, "%Y-%m-%dT%H:%M:%S")


def fetch():
    """Scarica e filtra il calendario. Ritorna la lista di eventi oppure None se non riesce."""
    try:
        r = requests.get(config.NEWS_URL, timeout=TIMEOUT, headers={"User-Agent": "Mozilla/5.0"})
        if not r.ok:
            print(f"Calendario notizie: HTTP {r.status_code}")
            return None
        data = r.json()
    except (requests.RequestException, ValueError) as e:
        print(f"Calendario notizie non raggiungibile: {type(e).__name__}")
        return None
    if not isinstance(data, list):
        return None
    out = []
    for ev in data:
        try:
            if str(ev.get("country", "")).upper() not in config.NEWS_CURRENCIES:
                continue
            if str(ev.get("impact", "")).capitalize() not in config.NEWS_IMPACT:
                continue
            t = datetime.fromisoformat(str(ev["date"]))
            if t.tzinfo is not None:
                t = t.astimezone(timezone.utc).replace(tzinfo=None)
            out.append({"t": _now_iso(t), "title": str(ev.get("title", "notizia"))[:60], "cur": str(ev.get("country", ""))})
        except (KeyError, ValueError, TypeError):
            continue
    out.sort(key=lambda e: e["t"])
    return out


def refresh(st, now_utc):
    """Aggiorna il calendario nello stato quando serve. Ritorna (eventi, disponibile)."""
    cal = st.get("news") or {}
    fetched = _parse(cal["fetched"]) if cal.get("fetched") else None
    tried = _parse(cal["tried"]) if cal.get("tried") else None
    need = fetched is None or (now_utc - fetched) > timedelta(hours=config.NEWS_REFRESH_HOURS)
    if need and (tried is None or (now_utc - tried) > timedelta(minutes=RETRY_MIN)):
        cal["tried"] = _now_iso(now_utc)
        ev = fetch()
        if ev is not None:
            cal["events"] = ev
            cal["fetched"] = _now_iso(now_utc)
            fetched = now_utc
        st["news"] = cal
    ok = fetched is not None and (now_utc - fetched) <= timedelta(hours=VALID_HOURS)
    return (cal.get("events", []) if ok else []), ok


def blocking_event(events, now_utc):
    """Evento forte che blocca i nuovi segnali adesso (da BEFORE minuti prima a AFTER minuti dopo), o None."""
    for e in events:
        t = _parse(e["t"])
        if t - timedelta(minutes=config.NEWS_BLOCK_BEFORE_MIN) <= now_utc <= t + timedelta(minutes=config.NEWS_BLOCK_AFTER_MIN):
            return e
    return None


def upcoming(events, now_utc, minutes):
    """Eventi che iniziano entro i prossimi `minutes` minuti."""
    return [e for e in events if timedelta(0) <= _parse(e["t"]) - now_utc <= timedelta(minutes=minutes)]


def of_day(events, day_rome, to_rome):
    """Eventi del giorno indicato (data italiana AAAA-MM-GG). to_rome converte un datetime UTC naive in ora italiana."""
    return [e for e in events if to_rome(_parse(e["t"])).strftime("%Y-%m-%d") == day_rome]


def label(e, to_rome):
    return f"{to_rome(_parse(e['t'])):%H:%M} {e['cur']} {e['title']}"
