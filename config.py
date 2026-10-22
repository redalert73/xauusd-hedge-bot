# config.py - Parametri di produzione ad alta selettività (Win Rate 67.74%)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Target di Rischio / Rendimento
SL_VAL = 2.300
TP_VAL = 2.000

# Parametri e Filtri di Ingresso (Ottimizzati per il massimo Win Rate)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0         # Filtro rigido per i rimbalzi VWAP di alta qualità
MOM_MULTIPLIER = 0.50        # Filtro rigido per il momentum
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo (in minuti da mezzanotte)
ORA_INIZIO_MINUTI = 6 * 60 + 0    # 06:00
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30

MAX_FUTURE_CANDLES = 4
