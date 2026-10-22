# config_breakout.py - Parametri di produzione Breakout (69.23% Win Rate)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Target di Rischio / Rendimento
SL_VAL = 2.300
TP_VAL = 2.000

# Parametri e Filtri di Ingresso
ATR_PERIOD = 14
VOL_MULTIPLIER = 1.8        
MOM_MULTIPLIER = 0.45       
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo
ORA_INIZIO_MINUTI = 5 * 60 + 45   # 05:45
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30

MAX_FUTURE_CANDLES = 4
