import pandas as pd
import numpy as np

def run(df: pd.DataFrame):
    """
    VWAP Contrarian Strategy (High Win-Rate Calibration)
    Filtra solo gli eccessi marcati e confermati da RSI/Bande.
    """
    if df.empty or len(df) < 30:
        return []

    signals = []
    
    # Calcolo VWAP cumulata/rolling
    df = df.copy()
    tp = (df['high'] + df['low'] + df['close']) / 3
    
    # Se il volume è presente nei dati
    if 'volume' in df.columns and df['volume'].sum() > 0:
        vwap = (tp * df['volume']).cumsum() / df['volume'].cumsum()
    else:
        vwap = tp.rolling(window=20).mean()

    std = tp.rolling(window=20).std()
    upper_band = vwap + (2.2 * std)  # Banda superiore stringente
    lower_band = vwap - (2.2 * std)  # Banda inferiore stringente

    # RSI per ulteriore conferma di ipercomprato/ipervenduto
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    for i in range(len(df) - 1, len(df) - 2, -1):
        row = df.iloc[i]
        dt = pd.to_datetime(row['datetime'])
        
        # Filtro orario 06:00 - 20:30 UTC
        if not (6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30)):
            continue

        price = row['close']
        c_rsi = rsi.iloc[i]

        if price > upper_band.iloc[i] and c_rsi > 68:
            signals.append((dt, "VWAP_SELL", price))
        elif price < lower_band.iloc[i] and c_rsi < 32:
            signals.append((dt, "VWAP_BUY", price))

    return signals
