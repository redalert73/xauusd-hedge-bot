import json
import os
from datetime import datetime
import config
import data_loader
from strategies import strategy_vwap, strategy_breakout, strategy_fibonacci
from notifier import send_notification, check_telegram_commands

STATE_FILE = "bot_state.json"

def is_bot_paused() -> bool:
    """Verifica se il bot è in pausa manuale o per circuito di protezione."""
    today = datetime.utcnow().strftime("%Y-%m-%d")
    
    manual_stop = check_telegram_commands()
    state = {"date": today, "paused": False, "notified": False}
    
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                loaded = json.load(f)
                if loaded.get("date") == today:
                    state = loaded
        except Exception as e:
            print(f"Impossibile leggere {STATE_FILE}: {e}")

    # Reset automatico per un nuovo giorno
    if state["date"] != today:
        state = {"date": today, "paused": False, "notified": False}

    # Attivazione nuova pausa via Telegram
    if manual_stop and not state["paused"]:
        state["paused"] = True
        if not state.get("notified"):
            send_notification("🛑 *COMANDO RICEVUTO*\nIl bot è stato messo in pausa per il resto della giornata. Nessun altro segnale verrà inviato fino a domani.")
            state["notified"] = True

    # Salva lo stato corrente
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except Exception as e:
        print(f"Errore nel salvataggio dello stato: {e}")

    return state["paused"]

def main():
    print("==================================================")
    print("🤖 ESECUZIONE SCANNER LIVE XAU/USD")
    print("==================================================")

    # 1. Verifico se l'utente ha richiesto la pausa
    if is_bot_paused():
        print("🛑 BOT IN PAUSA MANUALE: Scansione saltata come da richiesta su Telegram.")
        return

    # 2. Scaricamento dati di mercato
    df = data_loader.fetch_market_data()
    if df.empty:
        print("❌ Nessun dato disponibile.")
        return

    # 3. Controllo strategie
    signals_vwap = strategy_vwap.run(df)
    signals_breakout = strategy_breakout.run(df)
    signals_fib = strategy_fibonacci.run(df)

    all_signals = signals_vwap + signals_breakout + signals_fib

    if not all_signals:
        print("ℹ️ Nessun segnale operativo generato in questa scansione.")
        return

    # 4. Inoltro segnali trovati
    for dt, label, price in all_signals:
        msg = f"📊 *NUOVO SEGNALE XAU/USD*\n• *Strategia:* {label}\n• *Prezzo:* {price}\n• *Ora (UTC):* {dt.strftime('%H:%M')}\n\n⚙️ Lot Size: {config.LOT_SIZE} | SL: {config.SL_VAL} | TP: {config.TP_VAL}"
        print(f"🚀 Invio Notifica: {label} @ {price}")
        send_notification(msg)

if __name__ == "__main__":
    main()
