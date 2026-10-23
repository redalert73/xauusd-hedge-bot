import pandas as pd

def run(df: pd.DataFrame):
    if df.empty or len(df) < 20:
        return []

    signals = []
    df = df.copy()
    tp = (df['high'] + df['low'] + df['close']) / 3

    vwap = tp.rolling(window=14).mean()
    std = tp.rolling(window=14).std()
    
    # Deviazione bilanciata per intercettare gli eccessi senza bloccare tutto
    upper_band = vwap + (1.8 * std)
    lower_band = vwap - (1.8 * std)

    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
    rs = gain / loss
    rsi = 100 - (100 / (1 + rs))

    for i in range(1, len(df)):
        row = df.iloc[i]
        dt = pd.to_datetime(row['datetime'])

        if not (6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30)):
            continue

        price = row['close']
        c_rsi = rsi.iloc[i]

        if price > upper_band.iloc[i] and c_rsi > 65:
            signals.append((dt, "VWAP_SELL", price))
        elif price < lower_band.iloc[i] and c_rsi < 35:
            signals.append((dt, "VWAP_BUY", price))

    return signals
