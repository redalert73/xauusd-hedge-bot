# ==========================================
# CONFIGURAZIONE GLOBALE - BREAKOUT ELITE
# ==========================================

from datetime import datetime, timedelta

# Parametri operativi e dimensione lotto
LOT_SIZE = 1.04
SYMBOL = "XAU/USD"
TIMEFRAME = "15min"

# Finestra temporale dinamica per il backtest storico
START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
END_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

# Finestra operativa giornaliera (Sessione di Trading intraday M15)
SESSION_START = "08:00"
SESSION_END = "20:00"

# Parametri di rischio, target e punti
SL_VAL = 2400.0          # Target WIN principale in USD ($2.400)
TP_VAL = 2000.0          # Livello di LOSS da evitare in USD ($2.000)
SL_POINTS = 23.08        # Punti di Stop Loss associati

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
