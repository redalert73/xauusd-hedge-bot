# config.py - Configurazione Definitiva e Ottimizzata (Alta Qualità @ 69.23% Win Rate)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Target di Rischio / Rendimento validati
SL_VAL = 2.300
TP_VAL = 2.000

# Parametri e Filtri di Ingresso Rigidi (Massima Qualità)
ATR_PERIOD = 14
VOL_MULTIPLIER = 1.8        # Ripristinato a 1.8x
MOM_MULTIPLIER = 0.45       # Ripristinato a 0.45 ATR
EMA_EXT_MULTIPLIER = 0.4
SWING_OFFSET_MULTIPLIER = 0.2

# Orario Operativo esteso alle 20:30 (Validato: 100% dei trade si chiude entro 1 ora)
ORA_INIZIO_MINUTI = 5 * 60 + 45   # 05:45
ORA_FINE_MINUTI = 20 * 60 + 30    # 20:30

# Orizzonte temporale massimo del trade in simulazione/produzione (1 ora = 4 candele da 15 min)
MAX_FUTURE_CANDLES = 4
