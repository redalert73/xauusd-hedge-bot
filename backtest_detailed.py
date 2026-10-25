# ==========================================
# 🔵 [BACKTEST DETAILED] - ELENCO PUNTUALE E CONTEGGIO TP
# ==========================================

import pandas as pd
import numpy as np
import requests
import os

def download_twelve_data():
    api_key = os.getenv("TWELVE_DATA_API_KEY")
    if not api_key:
        print("❌ [DETAILED] ERRORE: TWELVE_DATA_API_KEY non trovata.")
        return None
    
    url = f"https://api.twelvedata.com/time_series?symbol=XAU/USD&interval=5min&outputsize=500&apikey={api_key}&timezone=UTC"
    response = requests.get(url)
    data = response.json()
    
    if "values" not in data:
        print("❌ [DETAILED] ERRORE nel recupero dati da Twelve Data.")
        return None
        
    df = pd.DataFrame(data["values"])
    df['datetime'] = pd.to_datetime(df['datetime'])
    df.set_index('datetime', inplace=True)
    df.sort_index(inplace=True)
    
    for col in ['open', 'high', 'low', 'close', 'volume']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
            
    return df

def run_detailed_backtest(df, strategy_module, strategy_name):
    print("\n" + "="*60)
    print(f"📊 [ACTION TYPE: BACKTEST DETAILED] -> Analisi: {strategy_name.upper()}")
    print("="*60)
    
    # Parametri definitivi bloccati
    lot_size = 1.04
    sl_usd = -2400.0
    tp_usd = 2000.0
    slippage_limit_per_trade = -2900.0  # Limite da non raggiungere mai sul singolo trade
    
    # Calcolo della conversione di prezzo per XAU/USD (1 lotto = 100 oz)
    dollar_per_point = lot_size * 100
    tp_distance = tp_usd / dollar_per_point
    sl_distance = abs(sl_usd) / dollar_per_point
    
    signals = strategy_module.run(df)
    if not signals:
        print(f"⚠️ [DETAILED] Nessun segnale generato per {strategy_name}.")
        return None
        
    detailed_trades = []
    accumulated_pnl = 0.0
    violating_trades_count = 0
    wins_count = 0
    losses_count = 0
    
    df_prices = df.copy()
    
    for idx, sig in enumerate(signals, 1):
        sig_time, sig_type, sig_price = sig
        
        try:
            start_loc = df_prices.index.get_loc(sig_time)
        except KeyError:
            continue
            
        if sig_type.upper() == 'BUY':
            target_tp = sig_price + tp_distance
            target_sl = sig_price - sl_distance
        else:
            target_tp = sig_price - tp_distance
            target_sl = sig_price + sl_distance
            
        trade_pnl = 0.0
        trade_result = "OPEN"
        
        for future_idx in range(start_loc + 1, len(df_prices)):
            row = df_prices.iloc[future_idx]
            h = row['high']
            l = row['low']
            
            if sig_type.upper() == 'BUY':
                hit_tp = h >= target_tp
                hit_sl = l <= target_sl
                if hit_tp and hit_sl:
                    trade_pnl = sl_usd
                    losses_count += 1
                    trade_result = "LOSS (SL)"
                    break
                elif hit_tp:
                    trade_pnl = tp_usd
                    wins_count += 1
                    trade_result = "WIN (TP)"
                    break
                elif hit_sl:
                    trade_pnl = sl_usd
                    losses_count += 1
                    trade_result = "LOSS (SL)"
                    break
            else:
                hit_tp = l <= target_tp
                hit_sl = h >= target_sl
                if hit_tp and hit_sl:
                    trade_pnl = sl_usd
                    losses_count += 1
                    trade_result = "LOSS (SL)"
                    break
                elif hit_tp:
                    trade_pnl = tp_usd
                    wins_count += 1
                    trade_result = "WIN (TP)"
                    break
                elif hit_sl:
                    trade_pnl = sl_usd
                    losses_count += 1
                    trade_result = "LOSS (SL)"
                    break
        else:
            trade_pnl = 0.0
            trade_result = "EXPIRED"

        accumulated_pnl += trade_pnl
        
        single_trade_breached = trade_pnl <= slippage_limit_per_trade
        if single_trade_breached:
            violating_trades_count += 1
            
        detailed_trades.append({
            'trade_id': idx,
            'time': sig_time,
            'type': sig_type.upper(),
            'price': round(sig_price, 2),
            'result': trade_result,
            'pnl ($)': trade_pnl,
            'cumulative_pnl ($)': accumulated_pnl,
            'single_trade_breached': single_trade_breached
        })
        
    df_trades = pd.DataFrame(detailed_trades)
    
    # Stampa dell'elenco puntuale di ogni singolo trade
    print("\n📋 ELENCO PUNTUALE SINGOLI TRADE:")
    print(df_trades.to_string(index=False))
    print("-" * 60)
    
    # Stampa del report riepilogativo con enfasi sui trade in TP
    print(f"📈 [DETAILED REPORT SUMMARY] -> {strategy_name.upper()}:")
    print(f"   - Totale Trade Eseguiti: {len(df_trades)}")
    print(f"   - 🎯 Totale Trade in Take Profit (TP): {wins_count}")
    print(f"   - ❌ Totale Trade in Stop Loss (SL): {losses_count}")
    print(f"   - Lotto: {lot_size} | SL: ${sl_usd:,.2f} | TP: ${tp_usd:,.2f}")
    print(f"   - Limite Singolo Trade (Slippage): ${slippage_limit_per_trade:,.2f}")
    print(f"   - Violazioni Limite Singolo: {violating_trades_count}")
    print(f"   - PnL Netto Complessivo: ${accumulated_pnl:,.2f}")
    print("="*60)
    
    return df_trades

def run_standalone():
    print("="*60)
    print("🚀 [ACTION TYPE: BACKTEST DETAILED] - ESECUZIONE AUTONOMA")
    print("="*60)
    df = download_twelve_data()
    if df is None or df.empty:
        print("❌ [DETAILED] Impossibile procedere senza dati di mercato.")
        return
        
    from strategies import strategy_breakout, strategy_vwap, strategy_fibonacci
    strategies = [
        (strategy_breakout, "Breakout Elite"),
        (strategy_vwap, "VWAP Strategy"),
        (strategy_fibonacci, "Fibonacci Strategy")
    ]
    
    for strat_mod, strat_name in strategies:
        run_detailed_backtest(df, strat_mod, strat_name)

if __name__ == "__main__":
    run_standalone()
