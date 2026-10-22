# config.py - Test con Stop Loss a 2.400

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Target di Rischio / Rendimento in test
SL_VAL = 2.400        # <-- Modificato a 2.400
TP_VAL = 2.000

# Parametri e Filtri di Ingresso Rigidi (Massima Qualità)
ATR_PERIOD = 14
VOL_MULTIPLIER = 1.8        
MOM_MULTIPLIER = 0.45       
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo esteso alle 20:30
ORA_INIZIO_MINUTI = 5 * 60 + 45   # 05:45
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30

# Orizzonte temporale massimo del trade (1 ora = 4 candele da 15 min)
MAX_FUTURE_CANDLES = 4
