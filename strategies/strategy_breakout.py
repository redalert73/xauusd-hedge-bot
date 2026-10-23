import pandas as pd

def run(df: pd.DataFrame):
    """
    Breakout Elite Strategy (Anti-Fakeout Calibration)
    Richiede rotture estese con margine di sicurezza per eliminare i falsi segnali.
    """
    if df.empty or len(df) < 30:
        return []

    signals = []
    df = df.copy()

    # Donchian Channels con margine anti-fakeout
    window = 24
    df['upper_channel'] = df['high'].shift(1).rolling(window=window).max()
    df['lower_channel'] = df['low'].shift(1).rolling(window=window).min()

    latest_row = df.iloc[-1]
    dt = pd.to_datetime(latest_row['datetime'])
    price = latest_row['close']

    # Filtro orario
    if 6 <= dt.hour < 20 or (dt.hour == 20 and dt.minute <= 30):
        # Tolleranza d'uscita per confermare la rottura reale
        buffer = 0.50  # 50 pips di margine oltre il canale
        
        if price > (latest_row['upper_channel'] + buffer):
            signals.append((dt, "BREAKOUT_BUY", price))
        elif price < (latest_row['lower_channel'] - buffer):
            signals.append((dt, "BREAKOUT_SELL", price))

    return signals
