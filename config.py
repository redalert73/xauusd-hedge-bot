# config.py - Parametri di produzione ottimizzati (~2 trade/giorno ad alta selettività)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Target di Rischio / Rendimento
SL_VAL = 2.300
TP_VAL = 2.000

# Parametri e Filtri di Ingresso (più restrittivi per aumentare la qualità dei Win)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0          # Portato da 1.8 a 2.0 per filtrare solo i rimbalzi VWAP più violenti
MOM_MULTIPLIER = 0.50         # Portato da 0.45 a 0.50 per filtrare solo i momentum più forti
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo (in minuti da mezzanotte)
ORA_INIZIO_MINUTI = 5 * 60 + 45   # 05:45
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30

MAX_FUTURE_CANDLES = 4
