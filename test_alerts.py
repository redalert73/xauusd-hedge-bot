# ==========================================
# TEST NOTIFICHE TELEGRAM
# ==========================================

import config
import notifier

if __name__ == "__main__":
    ok = notifier.send_notification(
        "Test bot hedge XAU/USD\n"
        f"Lotto {config.LOT_SIZE} | SL {config.SL_USD:,.0f}$ | TP {config.TP_USD:,.0f}$ | "
        f"slippage max {config.SLIPPAGE_MAX_USD:,.0f}$\n"
        f"Segnali {config.SIGNAL_START:%H:%M}-{config.SIGNAL_END:%H:%M} | chiusura {config.FORCE_CLOSE:%H:%M} (ora IT)\n"
        "Connessione Telegram verificata."
    )
    print("Telegram OK" if ok else "Telegram: invio NON riuscito")
    raise SystemExit(0 if ok else 1)
