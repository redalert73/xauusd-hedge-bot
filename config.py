# config.py - Configurazione Ottimale (Win Rate 66.67%)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Posizione e Rischio
LOT_SIZE = 1.04              # Dimensione posizione
SL_VAL = 2.400               # Target WIN (+2.400 USD)
TP_VAL = 2.000               # Target LOSS (-2.000 USD)
MAX_SLIPPAGE = 0.400

# Protezione Drawdown Giornaliero
MAX_DAILY_LOSS = 2000.0      # Blocco totale al verificarsi della 1a Loss nel giorno

# Filtri d'Ingresso Selettivi
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0
MOM_MULTIPLIER = 0.50
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo Completo
ORA_INIZIO_MINUTI = 6 * 60 + 0    # 06:00 UTC
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30 UTC

MAX_FUTURE_CANDLES = 4
