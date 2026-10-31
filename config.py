# ==========================================
# CONFIGURAZIONE GLOBALE - HEDGE XAU/USD (M5)
# ==========================================
# Schema operativo: ogni segnale apre una posizione sul broker "PERDENTE"
# e una speculare (direzione opposta) sul broker "SPECULARE".
#
#   Broker PERDENTE : l'obiettivo e' che tocchi lo SL (-2.200$).
#                     Il TP (+2.000$) e' l'esito da evitare.
#   Broker SPECULARE: conto reale, direzione opposta, lotti = MIRROR_LOT_RATIO x perdente.
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

# --- Broker SPECULARE (conto reale) ---
MIRROR_LOT_RATIO = 0.1                    # lotti speculare / lotti perdente (1 a 10): VERIFICA
MIRROR_LOT = round(LOT_SIZE * MIRROR_LOT_RATIO, 3)   # 0.104 lotti

# --- Obiettivo giornaliero ---
# Sul conto virtuale serve almeno UNO SL al giorno. Il bot non sa quali segnali
# esegui davvero: continua a inviare finche' non scrivi /fatto su Telegram.

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

# --- Fasce a liquidita' ridotta ---
# In queste fasce (ora italiana) il mercato e' piu' lento: spesso ne' SL ne' TP vengono toccati.
# Dentro una fascia il bot da un segnale solo se l'ATR e' almeno LOW_LIQUIDITY_ATR_RATIO volte la sua
# mediana degli ultimi 3 giorni (0 = filtro spento). Le fasce giuste vanno scelte con la tabella per ora
# di edge_scan.py, che stampa anche la riga pronta da incollare qui.
# Candidate tipiche dell'oro: 06:00-09:00 (Asia), 12:00-14:00 (pausa pranzo), 18:00-20:00 (sera).
LOW_LIQUIDITY_WINDOWS = [(time(18, 0), time(20, 0))]
LOW_LIQUIDITY_ATR_RATIO = 1.0

# --- Gestione segnali ---
# UN SOLO TRADE AL GIORNO: il bot propone segnali finche' non scrivi /eseguito su uno di essi.
# Da quel momento, qualunque sia l'esito (SL, TP o chiusura 21:45), nessun altro segnale per quel giorno.
# Se un segnale non viene confermato entro CONFIRM_TIMEOUT_MIN scade e puo' arrivarne un altro
# (fino a MAX_SIGNALS_PER_DAY proposte).
SINGLE_POSITION = True
# Conferma manuale: il bot traccia un segnale (SL/TP, stop del giorno) solo se scrivi /eseguito.
# Se non confermi entro CONFIRM_TIMEOUT_MIN minuti il segnale scade, non conta e puo' arrivarne un altro.
REQUIRE_CONFIRMATION = True
CONFIRM_TIMEOUT_MIN = 10
STOP_AFTER_EXECUTION = True   # dopo il primo segnale eseguito (confermato) niente altro per quel giorno
# Preset (validi solo con SINGLE_POSITION = False) (BASE_RELAX_LEVEL / TARGET / MAX / GAP):
#   qualita' prima  : 0 /  4 /  8 / 20   <- attuale: pochi segnali, i migliori per primi
#   piu' tentativi  : 1 /  8 / 20 / 10   (~10 segnali/giorno, ~10 posizioni aperte insieme)
#   massimo         : 1 / 12 / 30 /  5   (~15 segnali/giorno: poco in piu' sui giorni con SL)
BASE_RELAX_LEVEL = 0          # livelli sempre attivi: 0 = solo selettivo, 1 = + esteso. Livelli piu' larghi solo se sei in ritardo
TARGET_SIGNALS_PER_DAY = 1    # con posizione singola: entro il 60% della finestra il bot allenta i filtri finche' non esce il primo segnale
MAX_SIGNALS_PER_DAY = 4       # proposte al giorno: servono solo se non riesci a eseguire in tempo il primo
MIN_SIGNAL_GAP_MIN = 20       # distanza minima tra due segnali (evita raffiche sulla stessa mossa)
PACE_DEADLINE_FRAC = 0.6      # il target va raggiunto entro il 60% della finestra (~14:24): piu' tempo per risolversi
QUOTA_FRAC = 0.5              # oltre il 50% della finestra (~13:00), se sei sotto target scatta il livello "quota"
MAX_SIGNAL_AGE_MIN = 10       # scarta il segnale se la candela e' piu' vecchia di cosi'
CANDLES_TO_FETCH = 1500       # candele M5 per esecuzione (~5 giorni): servono a ATR mediano e VWAP
