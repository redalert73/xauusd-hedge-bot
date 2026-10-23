import pandas as pd
import config

# Parametri specifici Strategia Fibonacci
SWING_LOOKBACK = 30        # Barre per identificare gli Swing High / Low locali
FIB_MIN = 0.50             # Livello minimo Golden Zone (50.0%)
FIB_MAX = 0.618            # Livello massimo Golden Zone (61.8%)
STOP_LEVEL = 0.786         # Livello di invalidazione per Stop Loss (78.6%)


def run(df: pd.DataFrame) -> list:
    """Esegue la strategia Fibonacci Golden Zone e restituisce i segnali."""
    signals = []
    if df.empty:
        return signals

    # Calcolo degli Swing e dei livelli di Fibonacci
    df["rolling_high"] = df["high"].rolling(window=SWING_LOOKBACK).max()
    df["rolling_low"] = df["low"].rolling(window=SWING_LOOKBACK).min()
    
    df["fib_range"] = df["rolling_high"] - df["rolling_low"]
    
    df["fib_50_buy"] = df["rolling_high"] - (df["fib_range"] * FIB_MIN)
    df["fib_618_buy"] = df["rolling_high"] - (df["fib_range"] * FIB_MAX)
    df["fib_786_buy"] = df["rolling_high"] - (df["fib_range"] * STOP_LEVEL)
    
    df["fib_50_sell"] = df["rolling_low"] + (df["fib_range"] * FIB_MIN)
    df["fib_618_sell"] = df["rolling_low"] + (df["fib_range"] * FIB_MAX)
    df["fib_786_sell"] = df["rolling_low"] + (df["fib_range"] * STOP_LEVEL)

    # Scansione delle candele per individuare i segnali
    for i in range(SWING_LOOKBACK, len(df)):
        row = df.iloc[i]
        prev = df.iloc[i-1]
        
        dt = row["datetime"]
        current_minutes = dt.hour * 60 + dt.minute
        
        # Filtro orario basato su config.py
        if not (config.ORA_INIZIO_MINUTI <= current_minutes <= config.ORA_FINE_MINUTI):
            continue

        in_buy_zone = row["fib_618_buy"] <= row["close"] <= row["fib_50_buy"]
        rebound_buy = prev["close"] <= row["fib_618_buy"] and row["close"] > row["fib_618_buy"]
        
        in_sell_zone = row["fib_50_sell"] <= row["close"] <= row["fib_618_sell"]
        rebound_sell = prev["close"] >= row["fib_618_sell"] and row["close"] < row["fib_618_sell"]

        # Etichettatura chiara del segnale in linea con le altre strategie
        if in_buy_zone and rebound_buy:
            signals.append((dt, "[FIBONACCI] BUY (Golden Zone)", row["close"]))
        elif in_sell_zone and rebound_sell:
            signals.append((dt, "[FIBONACCI] SELL (Golden Zone)", row["close"]))
            
    return signals
