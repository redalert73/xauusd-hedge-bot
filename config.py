# config.py - Ottimizzazione Win Rate (Orario Ristretto 08:00-17:00 UTC + TP Ingrandito)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Posizione e Rischio
LOT_SIZE = 1.04              # Dimensione posizione
SL_VAL = 2.400               # Target WIN (+2.400 USD)
TP_VAL = 2.600               # Target LOSS (-2.600 USD) -> Più distante per proteggere il Win Rate
MAX_SLIPPAGE = 0.400

# Protezione Drawdown
MAX_DAILY_LOSS = 2400.0      # Max 1 Loss al giorno (blocco anti -3k$)

# Filtri Ottimizzati (Ritornati a 2.0 / 0.50 per non ritardare l'ingresso)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0
MOM_MULTIPLIER = 0.50
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo Ristretto (Solo sessioni liquide)
ORA_INIZIO_MINUTI = 8 * 60 + 0    # 08:00 UTC
ORA_FINE_MINUTI = 17 * 60 + 0     # 17:00 UTC

MAX_FUTURE_CANDLES = 4
