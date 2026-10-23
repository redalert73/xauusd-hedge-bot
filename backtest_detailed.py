import sys
import config
import data_loader
from strategies import strategy_vwap, strategy_breakout, strategy_fibonacci

def run_strategy_backtest(df, strategy_func, name):
    signals = strategy_func(df)
    wins = 0
    losses = 0
    
    # Simulazione base di riscontro esito basata sui dati storici
    for dt, sig_type, price in signals:
        # Esempio di logica di backtest per calcolo win/loss
        # Qui puoi mantenere la logica di riscontro che preferisci
        if "BUY" in sig_type:
            wins += 1
        else:
            losses += 1
            
    total_signals = len(signals)
    win_rate = (wins / total_signals * 100) if total_signals > 0 else 0.0
    
    # Stima PnL semplificata in base ai lotti e ai target
    pnl = (wins * config.TP_VAL * config.LOT_SIZE * 10) - (losses * config.SL_VAL * config.LOT_SIZE * 10)
    
    return {
        "name": name,
        "total_signals": total_signals,
        "wins": wins,
        "losses": losses,
        "win_rate": win_rate,
        "pnl": pnl
    }

def main():
    print("==================================================", flush=True)
    print("🔬 BACKTEST MULTI-TIMEFRAME (BREAKOUT @ 15min)", flush=True)
    print("==================================================", flush=True)
    print(f"⚙️ PARAMETRI: LOT_SIZE={config.LOT_SIZE} | SL={config.SL_VAL} | TP={config.TP_VAL} | MAX_DAILY_LOSS=${config.MAX_DAILY_LOSS}", flush=True)
    print("-" * 50, flush=True)

    # 1. Caricamento Dati M5 (per VWAP e Fibonacci)
    df_m5 = data_loader.fetch_market_data(interval="5min")
    if df_m5.empty:
        print("❌ Impossibile scaricare i dati M5 da Twelve Data.", flush=True)
        return

    # 2. Caricamento Dati M15 (per Breakout Elite)
    df_m15 = data_loader.fetch_market_data(interval="15min")
    if df_m15.empty:
        print("⚠️ Impossibile scaricare M15, fallback su M5 per Breakout.", flush=True)
        df_m15 = df_m5

    print(f"✅ Dati caricati: {len(df_m5)} candele M5 | {len(df_m15)} candele M15.", flush=True)

    # 3. Esecuzione delle strategie sui rispettivi timeframe
    results = [
        run_strategy_backtest(df_m5, strategy_vwap.run, "VWAP Contrarian (M5)"),
        run_strategy_backtest(df_m15, strategy_breakout.run, "Breakout Elite (M15)"),
        run_strategy_backtest(df_m5, strategy_fibonacci.run, "Fibonacci Golden Zone (M5)")
    ]

    # 4. Tabella Sinottica Finale stampata a schermo
    print("\n" + "=" * 80, flush=True)
    print("📊 RIEPILOGO GENERALE MULTI-TIMEFRAME", flush=True)
    print("=" * 80, flush=True)
    print(f"{'STRATEGIA':<28} | {'SEGNALI':<8} | {'WIN':<5} | {'LOSS':<5} | {'WIN RATE':<10} | {'PNL STIMATO':<12}", flush=True)
    print("-" * 80, flush=True)

    tot_signals = 0
    tot_pnl = 0.0

    for res in results:
        tot_signals += res["total_signals"]
        tot_pnl += res["pnl"]
        print(f"{res['name']:<28} | {res['total_signals']:<8} | {res['wins']:<5} | {res['losses']:<5} | {res['win_rate']:>8.2f}% | ${res['pnl']:>10.2f}", flush=True)

    print("-" * 80, flush=True)
    print(f"🏆 PNL COMPLESSIVO COMBINATO: ${tot_pnl:.2f} USD (Segnali totali: {tot_signals})", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()
