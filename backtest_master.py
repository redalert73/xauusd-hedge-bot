# ==========================================
# BACKTEST MASTER - MULTI-STRATEGIA XAU/USD
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
    print("🔄 BACKTEST MASTER - MULTI-STRATEGIA (XAU/USD | 5min)")
    print("=" * 50)
    
    lot_size = 1.04
    sl_usd = 2400.0
    tp_usd = 2000.0
    
    # Conversione USD in punti di prezzo per XAU/USD (1 lotto = 100 oz -> 1.04 lotti = 104 oz)
    sl_distance = sl_usd / (lot_size * 100)
    tp_distance = tp_usd / (lot_size * 100)
    
    print(f"🔹 Lotto: {lot_size} | Target WIN (SL): ${sl_usd} | Target LOSS (TP): ${tp_usd}")
    
    df = download_twelve_data()
    if df is None or df.empty:
        return
        
    # Filtro sessione operativa 08:00 - 20:00
    df = df.between_time('08:00', '20:00')
    
    print(f"🔹 Finestra Temporale Dinamica: da {df.index[0]} a {df.index[-1]}")
    print(f"🔹 Sessione Operativa: 08:00 - 20:00")
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
            # Filtro: escludiamo i segnali nell'ultima ora della sessione (dalle 19:00 in poi)
            if hasattr(sig_time, 'hour') and sig_time.hour >= 19:
                continue
            elif isinstance(sig_time, str):
                try:
                    hour_int = int(sig_time.split()[1].split(':')[0])
                    if hour_int >= 19:
                        continue
                except:
                    pass

            try:
                start_idx = df.index.get_loc(sig_time)
            except KeyError:
                continue
                
            # Simulazione forward bar-by-bar
            outcome = None
            pnl = 0.0
            
            for j in range(start_idx + 1, len(df)):
                c_high = df['high'].iloc[j]
                c_low = df['low'].iloc[j]
                
                if sig_type == "BUY":
                    hit_sl = c_low <= (sig_price - sl_distance)
                    hit_tp = c_high >= (sig_price + tp_distance)
                    
                    if hit_sl and hit_tp:
                        outcome = "LOSS"
                        pnl = -sl_usd
                        break
                    elif hit_sl:
                        outcome = "WIN_SL"
                        pnl = -sl_usd
                        break
                    elif hit_tp:
                        outcome = "LOSS_TP"
                        pnl = tp_usd
                        break
                        
                elif sig_type == "SELL":
                    hit_sl = c_high >= (sig_price + sl_distance)
                    hit_tp = c_low <= (sig_price - tp_distance)
                    
                    if hit_sl and hit_tp:
                        outcome = "LOSS"
                        pnl = -sl_usd
                        break
                    elif hit_sl:
                        outcome = "WIN_SL"
                        pnl = -sl_usd
                        break
                    elif hit_tp:
                        outcome = "LOSS_TP"
                        pnl = tp_usd
                        break
            
            if outcome is not None:
                trades.append({
                    'time': sig_time,
                    'type': sig_type,
                    'price': sig_price,
                    'outcome': outcome,
                    'pnl': pnl
                })
                
        if not trades:
            print(f"\n⚠️ Nessun trade completato per {strat_name} nel periodo specificato.\n")
            continue
            
        total_trades = len(trades)
        win_sl_count = sum(1 for t in trades if t['outcome'] == 'WIN_SL')
        win_rate = (win_sl_count / total_trades) * 100 if total_trades > 0 else 0
        total_pnl = sum(t['pnl'] for t in trades)
        
        print(f"\n📈 REPORT FINALE [{strat_name}]:")
        print(f"- Numero Totale Trade: {total_trades}")
        print(f"- Win Rate: {win_rate:.2f}%")
        print(f"- PnL Netto Complessivo: ${total_pnl:,.2f}\n")
        print("=" * 50)
        
    print("\n✅ BACKTEST MULTI-STRATEGIA COMPLETATO\n")

if __name__ == "__main__":
    run_backtest()
