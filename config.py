# ==========================================
# CONFIGURAZIONE CENTRALE - TRADING BOT
# ==========================================

SYMBOL = "XAU/USD"
INTERVAL = "15min"

LOT_SIZE = 1.04
SL_VAL = 2.400  # Target WIN (Raggiunto SL = Operazione in Guadagno)
TP_VAL = 2.000  # Target LOSS (Raggiunto TP = Operazione in Perdita)
MAX_SLIPPAGE = 0.400

# Circuit Breaker Anti-Drawdown Giornaliero (-3.000 USD Max)
MAX_DAILY_LOSS = 2400.0

# Parametri e Filtri d'Ingresso ad Alta Affidabilità
ATR_PERIOD = 14
VOL_MULTIPLIER = 1.80
MOM_MULTIPLIER = 0.50
SWING_OFFSET_MULTIPLIER = 0.18

# Finestra Operativa (06:00 - 20:30 UTC)
ORA_INIZIO_MINUTI = 6 * 60 + 0  # 06:00 UTC
ORA_FINE_MINUTI = 20 * 60 + 30  # 20:30 UTC
