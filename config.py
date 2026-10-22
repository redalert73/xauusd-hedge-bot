# Gestione Posizione e Rischio
LOT_SIZE = 1.04              
SL_VAL = 2.400               # Target WIN (Raggiunto SL = Operazione in Guadagno di 2.400)
TP_VAL = 2.000               # Target LOSS (Raggiunto TP = Operazione in Perdita di 2.000)

# Circuit Breaker Anti-Drawdown Giornaliero (Fissato per proteggere rigorosamente i -3.000 max)
MAX_DAILY_LOSS = 2400.0      # Si attiva subito dopo la prima perdita per blindare il tetto dei -3.000 USD
