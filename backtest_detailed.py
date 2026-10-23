def main():
    print("==================================================")
    print("🔬 BACKTEST MULTI-TIMEFRAME (BREAKOUT @ 15min)")
    print("==================================================")
    print(f"⚙️ PARAMETRI: LOT_SIZE={config.LOT_SIZE} | SL={config.SL_VAL} | TP={config.TP_VAL} | MAX_DAILY_LOSS=${config.MAX_DAILY_LOSS}")
    print("--------------------------------------------------")

    # 1. Caricamento Dati Standard (es. M5 per VWAP e Fibonacci)
    df_m5 = data_loader.fetch_market_data(interval="5min")
    if df_m5.empty:
        print("❌ Impossibile scaricare i dati M5 da Twelve Data.")
        return

    # 2. Caricamento Dati Dedicati per Breakout (M15)
    df_m15 = data_loader.fetch_market_data(interval="15min")
    if df_m15.empty:
        print("⚠️ Impossibile scaricare M15, fallback su M5 per Breakout.")
        df_m15 = df_m5

    print(f"✅ Dati caricati: {len(df_m5)} candele M5 | {len(df_m15)} candele M15.")

    # 3. Esecuzione delle strategie sui rispettivi timeframe
    results = [
        run_strategy_backtest(df_m5, strategy_vwap, "VWAP Contrarian (M5)"),
        run_strategy_backtest(df_m15, strategy_breakout, "Breakout Elite (M15)"),
        run_strategy_backtest(df_m5, strategy_fibonacci, "Fibonacci Golden Zone (M5)")
    ]

    # 4. Tabella Sinottica Finale
    print("\n" + "=" * 80)
    print("📊 RIEPILOGO GENERALE MULTI-TIMEFRAME")
    print("=" * 80)
    print(f"{'STRATEGIA':<28} | {'SEGNALI':<8} | {'WIN':<5} | {'LOSS':<5} | {'WIN RATE':<10} | {'PNL STIMATO':<12}")
    print("-" * 80)

    tot_signals = 0
    tot_pnl = 0.0

    for res in results:
        tot_signals += res["total_signals"]
        tot_pnl += res["pnl"]
        print(f"{res['name']:<28} | {res['total_signals']:<8} | {res['wins']:<5} | {res['losses']:<5} | {res['win_rate']:>8.2f}% | ${res['pnl']:>10.2f}")

    print("-" * 80)
    print(f"🏆 PNL COMPLESSIVO COMBINATO: ${tot_pnl:.2f} USD (Segnali totali: {tot_signals})")
    print("==================================================")
