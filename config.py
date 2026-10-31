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
LAST_SIGNAL_TIME = time(15, 0)  # dalle 15:00 nessun nuovo segnale: nel pomeriggio/sera SL e TP spesso non vengono toccati (dati reali)

# --- Fasce a liquidita' ridotta ---
# In queste fasce (ora italiana) il mercato e' piu' lento: spesso ne' SL ne' TP vengono toccati.
# Dentro una fascia il bot da un segnale solo se l'ATR e' almeno LOW_LIQUIDITY_ATR_RATIO volte la sua
# mediana degli ultimi 3 giorni (0 = filtro spento). Le fasce giuste vanno scelte con la tabella per ora
# di edge_scan.py, che stampa anche la riga pronta da incollare qui.
# Candidate tipiche dell'oro: 06:00-09:00 (Asia), 12:00-14:00 (pausa pranzo), 18:00-20:00 (sera).
LOW_LIQUIDITY_WINDOWS = []   # ora vuota: dopo LAST_SIGNAL_TIME non ci sono comunque segnali. Esempio: [(time(12, 0), time(14, 0))]
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
STOP_AFTER_EXECUTION = False  # True: dopo il primo segnale eseguito niente altro per quel giorno.
#   False = "riprova dopo un TP": dopo un TP (o chiusura senza esito) puo' arrivare un nuovo segnale; dopo lo SL si ferma.
#   Backtest (255 giorni): 2 tentativi con BASE_RELAX_LEVEL=1, TARGET=2, MAX=2, GAP=10 -> SL in ~64% dei giorni; 3 tentativi -> ~69%.
# Preset (validi solo con SINGLE_POSITION = False) (BASE_RELAX_LEVEL / TARGET / MAX / GAP):
#   qualita' prima  : 0 /  4 /  8 / 20   <- attuale: pochi segnali, i migliori per primi
#   piu' tentativi  : 1 /  8 / 20 / 10   (~10 segnali/giorno, ~10 posizioni aperte insieme)
#   massimo         : 1 / 12 / 30 /  5   (~15 segnali/giorno: poco in piu' sui giorni con SL)
BASE_RELAX_LEVEL = 1          # livelli sempre attivi: 0 = solo selettivo, 1 = + esteso. Livelli piu' larghi solo se sei in ritardo
TARGET_SIGNALS_PER_DAY = 2    # il bot allenta i filtri man mano che passa il tempo finche' non arrivano questi segnali
MAX_SIGNALS_PER_DAY = 2       # massimo di segnali al giorno: il secondo arriva solo dopo che il primo si e' chiuso in TP (dopo lo SL il bot si ferma)
MIN_SIGNAL_GAP_MIN = 10       # distanza minima tra due segnali (evita raffiche sulla stessa mossa)
PACE_DEADLINE_FRAC = 0.6      # il target va raggiunto entro il 60% della finestra (~14:24): piu' tempo per risolversi
QUOTA_FRAC = 0.5              # oltre il 50% della finestra (~13:00), se sei sotto target scatta il livello "quota"
MAX_SIGNAL_AGE_MIN = 10       # scarta il segnale se la candela e' piu' vecchia di cosi'
CANDLES_TO_FETCH = 1500       # candele M5 per esecuzione (~5 giorni): servono a ATR mediano e VWAP
