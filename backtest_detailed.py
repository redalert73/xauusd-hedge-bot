import os
import requests
import pandas as pd
import config

def fetch_market_data(interval=None):
    """
    Scarica i dati storici di mercato da Twelve Data.
    Supporta l'intervallo dinamico e recupera la chiave API 
    sia da config.py che dalle variabili d'ambiente di sistema/GitHub.
    """
    if interval is None:
        interval = getattr(config, "INTERVAL", "5min")

    symbol = getattr(config, "SYMBOL", "XAU/USD")
    
    # Recupera la chiave API da config o dalle variabili d'ambiente (GitHub Actions Secrets)
    api_key = getattr(config, "TWELVE_DATA_API_KEY", None)
    if not api_key:
        api_key = os.environ.get("TWELVE_DATA_API_KEY")

    if not api_key:
        print(f"❌ Errore critico: TWELVE_DATA_API_KEY non trovata né in config.py né nelle variabili d'ambiente.")
        return pd.DataFrame()

    # URL e parametri per l'API di Twelve Data
    url = f"https://api.twelvedata.com/time_series"
    params = {
        "symbol": symbol,
        "interval": interval,
        "outputsize": 500,
        "apikey": api_key,
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
