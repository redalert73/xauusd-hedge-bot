# config.py - Parametri di produzione definitivi (SL = 2.400, TP = 2.200)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Posizione e Rischio
LOT_SIZE = 1.04              # Dimensione della posizione (1.04 Lotti Standard)
SL_VAL = 2.400               # Stop Loss base (Target WIN = +2.400 USD)
TP_VAL = 2.200               # Take Profit base (Target LOSS = -2.200 USD)
MAX_SLIPPAGE = 0.400         # Tolleranza massimo slippage
MAX_SL_WITH_SLIPPAGE = SL_VAL + MAX_SLIPPAGE  # 2.800 (SL Max effettivo)

# Parametri e Filtri di Ingresso (Ottimizzati per il massimo Win Rate)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0         # Filtro rigido per i rimbalzi VWAP di alta qualità
MOM_MULTIPLIER = 0.50        # Filtro rigido per il momentum
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo (in minuti da mezzanotte)
ORA_INIZIO_MINUTI = 6 * 60 + 0    # 06:00 UTC
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30 UTC

MAX_FUTURE_CANDLES = 4
