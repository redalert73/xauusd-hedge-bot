# ==========================================
# CONFIGURAZIONE CENTRALE - TRADING BOT
# ==========================================

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Lotti e Valori di Rischio/Target ($2,400 per singolo trade)
LOT_SIZE = 1.04
SL_VAL = 23.08       # Distanza in punti dell'oro per rischiare $2,400 (con 1.04 lotti)
TP_VAL = 23.08       # Distanza in punti dell'oro per guadagnare $2,400 (R:R 1:1)
MAX_SLIPPAGE = 0.400

# Circuit Breaker Anti-Drawdown Giornaliero
MAX_DAILY_LOSS = 2400.0

# Parametri e Filtri d'Ingresso Ultra-Selettivi (Win Rate Massimizzato)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.00        # Innalzato per richiedere volumi più esplosivi
MOM_MULTIPLIER = 0.60        # Momentum più restrittivo per evitare falsi segnali
SWING_OFFSET_MULTIPLIER = 0.20 # Offset calibrato per ingressi chirurgici

# Finestra Operativa (06:00 - 20:30 UTC)
ORA_INIZIO_MINUTI = 6 * 60 + 0   # 06:00 UTC
ORA_FINE_MINUTI = 20 * 60 + 30   # 20:30 UTC
