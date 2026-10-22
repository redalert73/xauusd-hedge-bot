https://gemini.google.com/app/bf3b4d4fe37a7942?dest=create# config.py - Parametri condivisi per Backtest e Bot Live (XAU/USD)

SYMBOL = "XAU/USD"
INTERVAL = "15min"

# Target di Rischio / Rendimento validati
SL_VAL = 2.300
TP_VAL = 2.000

# Parametri e Filtri di Ingresso Ultra-Rigidi
ATR_PERIOD = 14
VOL_MULTIPLIER = 1.8        # Volume >= Media * 1.8
MOM_MULTIPLIER = 0.45       # Momentum >= ATR * 0.45
EMA_EXT_MULTIPLIER = 0.4    # Estensione EMA >= ATR * 0.4
SWING_OFFSET_MULTIPLIER = 0.2 # Rottura Swing >= ATR * 0.2

# Orario Operativo (UTC / Orario Server)
ORA_INIZIO_MINUTI = 5 * 60 + 45   # 05:45
ORA_FINE_MINUTI = 20 * 60         # 20:00
