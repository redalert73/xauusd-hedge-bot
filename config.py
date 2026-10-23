# ==========================================
# CONFIGURAZIONE GLOBALE - BREAKOUT ELITE
# ==========================================

# Parametri operativi e dimensione lotto
LOT_SIZE = 1.04
SYMBOL = "XAU/USD"
TIMEFRAME = "15min"

# Finestra temporale storica per il backtest (Data e Ora)
START_DATE = "2024-01-01 00:00:00"
END_DATE = "2026-10-01 23:59:59"

# Finestra operativa giornaliera (Sessione di Trading intraday M15)
# Filtra i segnali per operare solo durante le ore di massima liquidità
SESSION_START = "08:00"
SESSION_END = "20:00"

# Parametri di rischio e target in USD
SL_VAL = 2400.0  # Target WIN principale (in USD)
TP_VAL = 2000.0  # Livello di LOSS da evitare (in USD)

# Limiti di rischio e Circuit Breaker
MAX_DAILY_LOSS = 3000.0  # Limite massimo giornaliero da non raggiungere

# Filtri di attivazione e volatilità del Breakout
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0
MOMENTUM_THRESHOLD = 0.6
PRICE_OFFSET = 0.2

# Regola di formattazione report:
# - I risultati netti positivi (prevalenza di Win/SL) mostrano il segno "-"
# - I risultati negativi (prevalenza di Loss/TP) mostrano nessun segno (valore assoluto)
USE_MINUS_FOR_WINS = True
