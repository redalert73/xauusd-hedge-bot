# XAU/USD hedge bot

Segnali Telegram per la gamba perdente (conto virtuale) con speculare sul conto reale. Un solo trade al giorno.

- `live_bot.py` – bot (GitHub Actions ogni 5 minuti, lun-ven). Comandi Telegram: `/eseguito` `/stato` `/stop` `/ferma` `/pausa` `/riprendi` `/fatto`
- `backtest_hedge.py` – backtest su dati reali (workflow "Backtest Hedge", lasciare `optimize=false`)
- `edge_scan.py` – cerca condizioni con vantaggio reale e fasce a bassa liquidita' (workflow "Edge Scan")
- `convert_csv.py` – converte CSV Dukascopy o MetaTrader 5 nel formato del backtest (`--csv`)
- `config.py` – tutti i parametri
- `hedge_core.py`, `strategies/strategy_hedge.py`, `notifier.py` – logica comune

Secrets richiesti (Settings > Secrets > Actions): `TWELVE_DATA_API_KEY`, `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`.
