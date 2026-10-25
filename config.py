# ==========================================
# CONFIGURAZIONE GLOBALE - HEDGE XAU/USD (M5)
# ==========================================
# Schema operativo: ogni segnale apre una posizione sul broker "PERDENTE"
# e una speculare (direzione opposta) sul broker "SPECULARE".
#
#   Broker PERDENTE : l'obiettivo e' che tocchi lo SL (-2.200$).
#                     Il TP (+2.000$) e' l'esito da evitare.
#   Broker SPECULARE: direzione opposta, quindi TP = +2.200$ / SL = -2.000$.
#
# Tutti i valori in dollari sono riferiti al lotto indicato qui sotto.

from datetime import datetime, time, timedelta

# --- Mercato e dati (Twelve Data) ---
SYMBOL = "XAU/USD"
TIMEFRAME = "5min"
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
END_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# --- Posizione ---
LOT_SIZE = 1.04
OZ_PER_LOT = 100                          # 1 lotto standard XAU = 100 once
USD_PER_POINT = LOT_SIZE * OZ_PER_LOT     # 104$ per ogni 1.00 di prezzo

# --- Livelli di rischio (broker PERDENTE) ---
SL_USD = 2200.0           # OBIETTIVO dei segnali: la gamba perdente deve toccare lo SL
TP_USD = 2000.0           # esito da evitare
SLIPPAGE_MAX_USD = 2600.0 # perdita massima da non raggiungere mai

SL_POINTS = SL_USD / USD_PER_POINT                # ~21.15
TP_POINTS = TP_USD / USD_PER_POINT                # ~19.23
SLIPPAGE_POINTS = SLIPPAGE_MAX_USD / USD_PER_POINT  # 25.00

# --- Orari (sempre ora italiana, gestisce da solo ora legale/solare) ---
TIMEZONE = "Europe/Rome"
SIGNAL_START = time(6, 0)     # primo segnale inviabile
SIGNAL_END = time(20, 0)      # nessun nuovo segnale da questo orario
FORCE_CLOSE = time(21, 45)    # chiusura automatica di tutte le posizioni

# --- Gestione segnali ---
MAX_SIGNALS_PER_DAY = 4       # tetto giornaliero (0 = illimitato)
MAX_SIGNAL_AGE_MIN = 10       # scarta il segnale se la candela e' piu' vecchia di cosi'
CANDLES_TO_FETCH = 1500       # candele M5 per esecuzione (~5 giorni): servono a ATR mediano e VWAP
