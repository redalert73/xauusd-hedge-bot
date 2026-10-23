import sys
import config
import data_loader
from strategies import strategy_vwap, strategy_breakout, strategy_fibonacci

def run_strategy_backtest(df, strategy_func, name):
    if df.empty:
        print(f"⚠️ Attenzione: Il DataFrame per {name} è vuoto!", flush=True)
        return {"name": name, "total_signals": 0, "wins": 0, "losses": 0, "win_rate": 0.0, "pnl": 0.0}
    
    signals = strategy_func(df)
    wins = 0
    losses = 0
    
    for dt, sig_type, price in signals:
        if "BUY" in sig_type or "LONG" in sig_type:
            wins += 1
        else:
            losses += 1
            
    total_signals = len(signals)
    win_rate = (wins / total_signals * 100) if total_signals > 0 else 0.0
    
    # Calcolo PnL grezzo basato su Win = SL_VAL e Loss = TP_VAL
    point_value = 100 * config.LOT_SIZE
    raw_pnl = (wins * config.SL_VAL * point_value) - (losses * config.TP_VAL * point_value)
    
    # Applicazione della regola sui segni richiesta:
    # - Se prevalgono le Win (SL), il PnL finale mostra il segno "-"
    # - Se prevalgono le Loss (TP), il PnL finale mostra nessun segno (valore assoluto positivo)
    if raw_pnl > 0:
        pnl = -raw_pnl
    elif raw_pnl < 0:
        pnl = abs(raw_pnl)
    else:
        pnl = 0.0
    
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
    print("🔬 BACKTEST MULTI-TIMEFRAME (VWAP/FIBO @ 5min | BREAKOUT @ 15min)", flush=True)
    print("==================================================", flush=True)
    print(f"⚙️ PARAMETRI: LOT_SIZE={config.LOT_SIZE} | SL={config.SL_VAL} | TP={config.TP_VAL} | MAX_DAILY_LOSS=${config.MAX_DAILY_LOSS}", flush=True)
    print("-" * 50, flush=True)

    # 1. Caricamento Dati M5 (per le 2 strategie a 5 minuti: VWAP e Fibonacci)
    df_m5 = data_loader.fetch_market_data(interval="5min")
    if df_m5.empty:
        print("❌ ERRORE CRITICO: Impossibile scaricare i dati M5 da Twelve Data.", flush=True)
        sys.exit(1)
    print(f"✅ Dati M5 (VWAP & Fibonacci) scaricati con successo: {len(df_m5)} candele.", flush=True)

    # 2. Caricamento Dati M15 (per Breakout Elite)
    df_m15 = data_loader.fetch_market_data(interval="15min")
    if df_m15.empty:
        print("⚠️ Impossibile scaricare M15, eseguo fallback su M5 per Breakout.", flush=True)
        df_m15 = df_m5
    else:
        print(f"✅ Dati M15 (Breakout Elite) scaricati con successo: {len(df_m15)} candele.", flush=True)

    # 3. Esecuzione delle strategie sui rispettivi timeframe
    results = [
        run_strategy_backtest(df_m5, strategy_vwap.run, "VWAP Contrarian (5 min)"),
        run_strategy_backtest(df_m15, strategy_breakout.run, "Breakout Elite (15 min)"),
        run_strategy_backtest(df_m5, strategy_fibonacci.run, "Fibonacci Golden Zone (5 min)")
    ]

    # 4. Tabella Sinottica Finale
    print("\n" + "=" * 80, flush=True)
    print("📊 RIEPILOGO GENERALE MULTI-TIMEFRAME", flush=True)
    print("=" * 80, flush=True)
    print(f"{'STRATEGIA & TIMEFRAME':<30} | {'SEGNALI':<8} | {'WIN':<5} | {'LOSS':<5} | {'WIN RATE':<10} | {'PNL STIMATO':<12}", flush=True)
    print("-" * 80, flush=True)

    tot_signals = 0
    tot_pnl = 0.0

    for res in results:
        tot_signals += res["total_signals"]
        tot_pnl += res["pnl"]
        print(f"{res['name']:<30} | {res['total_signals']:<8} | {res['wins']:<5} | {res['losses']:<5} | {res['win_rate']:>8.2f}% | ${res['pnl']:>10.2f}", flush=True)

    print("-" * 80, flush=True)
    print(f"🏆 PNL COMPLESSIVO COMBINATO: ${tot_pnl:.2f} USD (Segnali totali: {tot_signals})", flush=True)
    print("==================================================", flush=True)

if __name__ == "__main__":
    main()
