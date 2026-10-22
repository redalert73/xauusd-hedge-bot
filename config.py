# config.py - Parametri di produzione con SL/TP e Slippage aggiornati

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Gestione Posizione e Rischio
LOT_SIZE = 5.55              # Dimensione della posizione (5.55 Lotti Standard)
TP_VAL = 2.000               # Take Profit (Target perdita per la regola d'esito)
SL_VAL = 2.400               # Stop Loss (Target vittoria per la regola d'esito)
MAX_SLIPPAGE = 0.400         # Toleranza massimo slippage (SL max effettivo = 2.800)
MAX_SL_WITH_SLIPPAGE = SL_VAL + MAX_SLIPPAGE  # 2.800

# Parametri e Filtri di Ingresso (Ottimizzati per il massimo Win Rate)
ATR_PERIOD = 14
VOL_MULTIPLIER = 2.0         # Filtro rigido per i rimbalzi VWAP di alta qualità
MOM_MULTIPLIER = 0.50        # Filtro rigido per il momentum
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo (in minuti da mezzanotte)
ORA_INIZIO_MINUTI = 6 * 60 + 0    # 06:00
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30

MAX_FUTURE_CANDLES = 4
