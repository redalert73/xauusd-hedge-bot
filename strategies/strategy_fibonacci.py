import pandas as pd

def run(df: pd.DataFrame):
    """
    Fibonacci Golden Zone Strategy (High Precision Calibration)
    Accetta ingressi solo nel livello aureo 61.8% - 78.6%.
    """
    if df.empty or len(df) < 50:
        return []

    signals = []
    df = df.copy()
    
    # Calcolo High e Low significativi delle ultime 40 candele
    lookback = 40
    recent_high = df['high'].tail(lookback).max()
    recent_low = df['low'].tail(lookback).min()
    diff = recent_high - recent_low

    if diff == 0:
        return []

    # Livelli di Fibonacci
    fib_618 = recent_high - (diff * 0.618)
    fib_786 = recent_high - (diff * 0.786)

    latest_row = df.iloc[-1]
    dt = pd.to_datetime(latest_row['datetime'])
    price = latest_row['close']

    # Filtro orario
    if 6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30):
        # In ingresso rialzista su zona aurea dopo ritracciamento
        if fib_786 <= price <= fib_618 and price > df['close'].iloc[-2]:
            signals.append((dt, "FIBO_GOLDEN_BUY", price))

    return signals
