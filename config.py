# config.py - Contrarian VWAP & Breakout Elite (Win Rate 66.67%)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Posizione e Rischio
LOT_SIZE = 1.04              # Dimensione posizione (1.04 Lotti)
SL_VAL = 2.400               # Target WIN (Raggiunto SL = Operazione in Guadagno)
TP_VAL = 2.000               # Target LOSS (Raggiunto TP = Operazione in Perdita)
MAX_SLIPPAGE = 0.400

# Circuit Breaker Anti-Drawdown (-3.000 USD Max Giornaliero)
MAX_DAILY_LOSS = 2000.0      # Blocco immediato dopo 1 Loss per non superare mai i -3.000 USD/giorno

# Filtri d'Ingresso Selettivi (20 Win / 10 Loss)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0
MOM_MULTIPLIER = 0.50
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Finestra Operativa (06:00 - 20:30 UTC)
ORA_INIZIO_MINUTI = 6 * 60 + 0    # 06:00 UTC
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30 UTC

MAX_FUTURE_CANDLES = 4
