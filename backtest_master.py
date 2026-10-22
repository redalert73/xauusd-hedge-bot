import os
import sys
import pandas as pd
import numpy as np

# Definizione configurazioni interne al backtest per massima sicurezza e autonomia
SYMBOL = "XAU/USD"
INTERVAL = "15min"
LOT_SIZE = 1.04
SL_VAL = 2.400
TP_VAL = 2.000
MAX_DAILY_LOSS = 2400.0

def main():
    print(f"🔄 Avvio Backtest Master: Contrarian VWAP & Breakout Elite ({SYMBOL} - {INTERVAL})...")
    print(f"Parametri attivi -> Lotto: {LOT_SIZE} | Target WIN (SL): {SL_VAL} | Target LOSS (TP): {TP_VAL}")
    print("Ambiente di backtest configurato e pronto all'uso.")

if __name__ == "__main__":
    main()
    
