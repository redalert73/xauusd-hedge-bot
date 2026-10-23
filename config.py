# ==========================================
# CONFIGURAZIONE GLOBALE - MODULARE
# ==========================================

from datetime import datetime, timedelta

LOT_SIZE = 1.04
SYMBOL = "XAU/USD"
TIMEFRAME = "15min"

START_DATE = (datetime.now() - timedelta(days=365)).strftime("%Y-%m-%d %H:%M:%S")
END_DATE = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

SESSION_START = "08:00"
SESSION_END = "20:00"

# Parametri di rischio e target ottimali
SL_VAL = 2400.0          # Target WIN principale ($2.400)
TP_VAL = 2000.0          # Livello di LOSS da evitare ($2.000)
SL_POINTS = 23.08        # Punti di Stop Loss

MAX_DAILY_LOSS = 3000.0  # Circuit Breaker

# Parametri originali del Breakout (quelli che hanno generato i risultati positivi)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0     # Moltiplicatore volume ottimale
MOMENTUM_THRESHOLD = 0.6 # Soglia momentum ottimale
PRICE_OFFSET = 0.2       # Offset di prezzo

# Regola di formattazione PnL: Netto positivo preceduto da "-"
USE_MINUS_FOR_WINS = True
