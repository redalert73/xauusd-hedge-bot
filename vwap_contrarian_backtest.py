# Aumentiamo le deviazioni standard a 2.2 per filtrare solo i veri estremi
vwap, upper_band, lower_band = calcola_vwap_e_bande(candles, i, num_std=2.2)

segnale = None
tp, sl = 0.0, 0.0

# Ingresso più selettivo: richiede che sia la chiusura (o un movimento forte) a rompere la banda
if prezzo_chiusura >= upper_band:
    segnale = "SELL"
    sl = prezzo_chiusura + config.SL_VAL
    tp = prezzo_chiusura - config.TP_VAL
elif prezzo_chiusura <= lower_band:
    segnale = "BUY"
    sl = prezzo_chiusura - config.SL_VAL
    tp = prezzo_chiusura + config.TP_VAL
