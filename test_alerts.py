# ==========================================
# TEST NOTIFICHE TELEGRAM + PULSANTI
# ==========================================
# Invia un messaggio con la tastiera, poi aspetta fino a ~90 secondi che tu prema un pulsante
# e risponde confermando. I comandi letti qui vengono consumati: il Live Bot non li rivedra'.

import time

import config
import hedge_core as core
import news
import notifier

WAIT_SECONDS = 90

if __name__ == "__main__":
    ok = notifier.send_notification(
        "Test bot hedge XAU/USD\n"
        f"Lotto {config.LOT_SIZE} | mirror {config.MIRROR_LOT} | SL {config.SL_USD:,.0f}$ | TP {config.TP_USD:,.0f}$ | "
        f"slippage max {config.SLIPPAGE_MAX_USD:,.0f}$\n"
        f"Segnali {config.SIGNAL_START:%H:%M}-{config.SIGNAL_END:%H:%M} (ultimo {config.LAST_SIGNAL_TIME:%H:%M}) | "
        f"chiusura {config.FORCE_CLOSE:%H:%M} (ora IT)\n"
        "Connessione Telegram verificata."
    )
    print("Telegram OK" if ok else "Telegram: invio NON riuscito")
    if not ok:
        raise SystemExit(1)

    # Calendario notizie: verifica che la fonte risponda e mostra le notizie forti della settimana.
    if config.NEWS_FILTER:
        ev = news.fetch()
        if ev is None:
            notifier.send_notification("Calendario notizie: NON raggiungibile in questo momento. Riprova piu' tardi; se continua, avvisami.")
        else:
            righe = "\n".join(f"{core.to_rome(e['t']):%a %d/%m} {news.label(e, core.to_rome)}" for e in ev) or "nessuna"
            notifier.send_notification(f"Calendario notizie OK. Notizie forti di questa settimana (ora IT):\n{righe}")
        print("Calendario notizie:", "non raggiungibile" if ev is None else f"{len(ev)} notizie forti")

    notifier.send_notification(
        f"Prova pulsanti: premi Eseguito qui sotto (o un tasto della tastiera) entro {WAIT_SECONDS} secondi.\n"
        "Evita Pausa e Fatto: in test non cambiano nulla, ma tieni la prova semplice."
    )

    # Salta eventuali comandi vecchi e parte dal piu' recente.
    _, offset = notifier.fetch_commands(0)
    _, offset = notifier.fetch_commands(offset)
    end = time.time() + WAIT_SECONDS
    got = None
    while time.time() < end and not got:
        time.sleep(3)
        cmds, offset = notifier.fetch_commands(offset)
        if cmds:
            got = cmds[0]
    if got:
        notifier.send_notification(f"Pulsante ricevuto: {got}. Funziona. (In produzione il Live Bot lo legge ogni 5 minuti, lun-ven.)")
        notifier.fetch_commands(offset)      # conferma a Telegram che sono stati letti
        print(f"Pulsante ricevuto: {got}")
    else:
        notifier.send_notification("Nessun pulsante premuto entro il tempo: prova non completata. Rilancia Test Alerts e premilo subito.")
        print("Nessun pulsante premuto")
