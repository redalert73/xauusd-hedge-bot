import pandas as pd
import config

def run(df: pd.DataFrame) -> list:
    """Esegue la strategia VWAP Contrarian e restituisce i segnali."""
    signals = []
    if df.empty:
        return signals

    # Calcolo della VWAP o media mobile di fallback in assenza di volume
    df["typical_price"] = (df["high"] + df["low"] + df["close"]) / 3
    if "volume" in df.columns and df["volume"].sum() > 0:
        df["vwap"] = (df["typical_price"] * df["volume"]).cumsum() / df["volume"].cumsum()
    else:
        df["vwap"] = df["typical_price"].rolling(window=14).mean()

    for i in range(14, len(df)):
        row = df.iloc[i]
        dt = row["datetime"]
        
        current_mins = dt.hour * 60 + dt.minute
        if not (config.ORA_INIZIO_MINUTI <= current_mins <= config.ORA_FINE_MINUTI):
            continue
        
        # Segnali VWAP Contrarian
        if row["close"] < row["vwap"] * 0.998:
            signals.append((dt, "[VWAP] BUY (Contrarian)", row["close"]))
        elif row["close"] > row["vwap"] * 1.002:
            signals.append((dt, "[VWAP] SELL (Contrarian)", row["close"]))
            
    return signals
