# config.py - Configurazione con TP 2.000 e Orario Ristretto (08:00 - 17:00 UTC)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Posizione e Rischio
LOT_SIZE = 1.04              # Dimensione della posizione (1.04 Lotti)
SL_VAL = 2.400               # Stop Loss base (Target WIN = +2.400 USD)
TP_VAL = 2.000               # Take Profit base (Target LOSS = -2.000 USD)
MAX_SLIPPAGE = 0.400         # Tolleranza massimo slippage

# Protezione Drawdown Giornaliero (Circuit Breaker)
MAX_DAILY_LOSS = 2000.0      # Blocco totale delle operazioni se si registra 1 Loss nel giorno

# Parametri e Filtri d'Ingresso (Ottimizzati)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0         # Filtro selettività standard
MOM_MULTIPLIER = 0.50        # Filtro momentum standard
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo Ristretto (Solo sessioni ad alta liquidità)
ORA_INIZIO_MINUTI = 8 * 60 + 0    # 08:00 UTC
ORA_FINE_MINUTI = 17 * 60 + 0     # 17:00 UTC

MAX_FUTURE_CANDLES = 4
