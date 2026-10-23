# ==========================================
# BACKTEST MASTER - MULTI-STRATEGIA XAU/USD (FORZATURA SOLO SL)
# ==========================================

import os
import pandas as pd
import requests
from datetime import datetime

# Import delle strategie
from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci

def download_twelve_data():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("❌ ERRORE: TWELVE_DATA_API_KEY non trovata nelle variabili d'ambiente.")
        return None
    
    print("✅ TWELVE_DATA_API_KEY rilevata. Scaricamento dati da Twelve Data per XAU/USD (5min)...")
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=5000&apikey={api_key}&timezone=UTC"
    
    response = requests.get(url)
    data = response.json()
    
    if "values" not in data:
        print(f"❌ Errore nel download dei dati: {data}")
        return None
        
    df = pd.DataFrame(data["values"])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def run_backtest():
    print("=" * 50)
    print("🔄 BACKTEST MASTER - FORZATURA TOTALE SL (PASSIVO MASSIMO)")
    print("=" * 50)
    
    lot_size = 1.04
    sl_usd = 2400.0  # Impatto negativo per ogni SL (-$2,400)
    
    print(f"🔹 Lotto: {lot_size} | Esito Forzato per ogni trade: SL (-${sl_usd})")
    
    df = download_twelve_data()
    if df is None or df.empty:
        return
        
    # Filtro sessione operativa 08:00 - 20:00 (escludendo l'ultima ora per dati troncati)
    df = df.between_time('08:00', '20:00')
    
    print(f"🔹 Finestra Temporale Dinamica: da {df.index[0]} a {df.index[-1]}")
    print(f"🔹 Sessione Operativa: 08:00 - 20:00 (Esclusa 19:00-20:00)")
    print("-" * 50)
    
    strategies_registry = {
        "Breakout Elite": strategy_breakout,
        "VWAP Strategy": strategy_vwap,
        "Fibonacci Strategy": strategy_fibonacci
    }
    
    for strat_name, strat_module in strategies_registry.items():
        print("=" * 50)
        print(f"📊 ESECUZIONE STRATEGIA: {strat_name.upper()}")
        print("=" * 50)
        
        signals = strat_module.run(df)
        print(f"- Segnali totali generati: {len(signals)}")
        
        trades = []
        
        for sig_time, sig_type, sig_price in signals:
            # Filtro ultima ora (dalle 19:00 in poi)
            if hasattr(sig_time, 'hour') and sig_time.hour >= 19:
                continue
            elif isinstance(sig_time, str):
                try:
                    hour_int = int(sig_time.split()[1].split(':')[0])
                    if hour_int >= 19:
                        continue
                except:
                    pass

            # FORZATURA ASSOLUTA: Ogni trade valido genera un SL (-$2,400)
            trades.append({
                'time': sig_time,
                'type': sig_type,
                'price': sig_price,
                'outcome': 'WIN_SL',
                'pnl': -sl_usd
            })
                
        if not trades:
            print(f"\n⚠️ Nessun trade generato per {strat_name}.\n")
            continue
            
        total_trades = len(trades)
        total_pnl = sum(t['pnl'] for t in trades)
        
        print(f"\n📈 REPORT FINALE [{strat_name}]:")
        print(f"- Numero Totale Trade: {total_trades}")
        print(f"- Win Rate (su SL): 100.00% ({total_trades} SL su {total_trades})")
        print(f"- PnL Netto Complessivo (Passivo): ${total_pnl:,.2f}\n")
        print("=" * 50)
        
    print("\n✅ BACKTEST CON FORZATURA SL COMPLETATO\n")

if __name__ == "__main__":
    run_backtest()
