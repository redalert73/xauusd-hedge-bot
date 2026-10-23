import pandas as pd
import config

def run(df: pd.DataFrame) -> list:
    """Esegue la strategia Breakout Elite e restituisce i segnali."""
    signals = []
    if df.empty:
        return signals

    lookback = 20
    df["resistance"] = df["high"].rolling(window=lookback).max().shift(1)
    df["support"] = df["low"].rolling(window=lookback).min().shift(1)

    for i in range(lookback + 1, len(df)):
        row = df.iloc[i]
        dt = row["datetime"]
        
        current_mins = dt.hour * 60 + dt.minute
        if not (config.ORA_INIZIO_MINUTI <= current_mins <= config.ORA_FINE_MINUTI):
            continue

        # Segnali Breakout Elite
        if row["close"] > row["resistance"]:
            signals.append((dt, "[BREAKOUT] BUY (Resistenza rotta)", row["close"]))
        elif row["close"] < row["support"]:
            signals.append((dt, "[BREAKOUT] SELL (Supporto rotto)", row["close"]))
            
    return signals
