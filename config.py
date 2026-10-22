# config.py - Parametri aggiornati (Filtri più ampi & Orario esteso)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Target di Rischio / Rendimento validati
SL_VAL = 2.300
TP_VAL = 2.000

# Parametri e Filtri di Ingresso (Rilassati per aumentare la frequenza)
ATR_PERIOD = 14
VOL_MULTIPLIER = 1.6        # Ridotto da 1.8 a 1.6
MOM_MULTIPLIER = 0.4        # Ridotto da 0.45 a 0.4
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo esteso fino alle 20:30
ORA_INIZIO_MINUTI = 5 * 60 + 45   # 05:45
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30 (Esteso)

# Orizzonte temporale massimo del trade in simulazione (1 ora = 4 candele da 15 min)
MAX_FUTURE_CANDLES = 4
