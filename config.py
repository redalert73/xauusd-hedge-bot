# config.py - Configurazione Ultra-Selettiva con Circuit Breaker anti-Drawdown

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Posizione e Rischio
LOT_SIZE = 1.04              # Dimensione della posizione (1.04 Lotti Standard)
SL_VAL = 2.400               # Stop Loss (Target WIN)
TP_VAL = 2.200               # Take Profit (Target LOSS = -2.400 USD)
MAX_SLIPPAGE = 0.400         # Tolleranza massimo slippage

# Protezione Drawdown Giornaliero (Circuit Breaker)
MAX_DAILY_LOSS = 2400.0      # Blocco totale delle operazioni se si registra 1 Loss nel giorno

# Filtri d'Ingresso Inaspriti (Per alzare ulteriormente il Win Rate)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.5         # Aumentato da 2.0 -> Solo setup ad altissima qualità
MOM_MULTIPLIER = 0.75        # Aumentato da 0.50 -> Momentum di conferma più forte
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo
ORA_INIZIO_MINUTI = 6 * 60 + 0    # 06:00 UTC
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30 UTC

MAX_FUTURE_CANDLES = 4
