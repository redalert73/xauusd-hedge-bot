import pandas as pd

def run(df: pd.DataFrame):
    if df.empty or len(df) < 15:
        return []

    signals = []
    df = df.copy()

    # Canale Donchian ridotto per adattarsi alle candele veloci
    window = 12
    df['upper_channel'] = df['high'].shift(1).rolling(window=window).max()
    df['lower_channel'] = df['low'].shift(1).rolling(window=window).min()

    for i in range(window, len(df)):
        row = df.iloc[i]
        dt = pd.to_datetime(row['datetime'])

        if not (6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30)):
            continue

        price = row['close']
        buffer = 0.20  # Buffer ottimizzato per M5

        if price > (row['upper_channel'] + buffer):
            signals.append((dt, "BREAKOUT_BUY", price))
        elif price < (row['lower_channel'] - buffer):
            signals.append((dt, "BREAKOUT_SELL", price))

    return signals
