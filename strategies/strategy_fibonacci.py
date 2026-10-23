import pandas as pd

def run(df: pd.DataFrame):
    if df.empty or len(df) < 25:
        return []

    signals = []
    df = df.copy()

    lookback = 20
    
    for i in range(lookback, len(df)):
        sub_df = df.iloc[i-lookback:i]
        recent_high = sub_df['high'].max()
        recent_low = sub_df['low'].min()
        diff = recent_high - recent_low

        if diff == 0:
            continue

        fib_618 = recent_high - (diff * 0.618)
        fib_786 = recent_high - (diff * 0.786)

        row = df.iloc[i]
        dt = pd.to_datetime(row['datetime'])

        if not (6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30)):
            continue

        price = row['close']
        prev_price = df['close'].iloc[i-1]

        if fib_786 <= price <= fib_618 and price > prev_price:
            signals.append((dt, "FIBO_GOLDEN_BUY", price))

    return signals
