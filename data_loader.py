import requests
import pandas as pd
import config

def fetch_market_data(interval=None):
    """
    Scarica i dati storici di mercato da Twelve Data.
    Accetta un parametro opzionale 'interval'. Se non specificato, 
    utilizza il valore di default impostato in config.INTERVAL.
    """
    if interval is None:
        interval = getattr(config, "INTERVAL", "5min")

    symbol = getattr(config, "SYMBOL", "XAU/USD")
    
    # URL e parametri per l'API di Twelve Data
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 500,
        "apikey": config.TWELVE_DATA_API_KEY,
        "format": "JSON"
    }

    try:
        response = requests.get(url, params=params)
        data = response.json()

        if "values" in data:
            df = pd.DataFrame(data["values"])
            # Riconverte le colonne numeriche e la data
            df['datetime'] = pd.to_datetime(df['datetime'])
            for col in ['open', 'high', 'low', 'close', 'volume']:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Ordina in ordine cronologico crescente
            df = df.sort_values('datetime').reset_index(drop=True)
            return df
        else:
            print(f"⚠️ Errore nel recupero dati per {interval}: {data.get('message', 'Risposta non valida')}")
            return pd.DataFrame()

    except Exception as e:
        print(f"❌ Eccezione durante la chiamata API Twelve Data ({interval}): {e}")
        return pd.DataFrame()
