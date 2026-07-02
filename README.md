# NSE Option Chain Trade Analyzer

Fetches live Nifty/BankNifty option-chain data from NSE every 5 minutes,
computes positioning metrics (PCR, Max Pain, OI support/resistance, IV skew),
optionally asks a local Ollama model to summarize it in plain English, and
sends the result to you on Telegram.

**Not financial advice.** This tool describes what current options
positioning implies; it does not predict price and should not be the sole
basis for trading decisions.

---

## 1. Setup

```bash
git clone <your-repo-url>
cd nse_trade_analyzer
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
```

Edit `.env`:
- `NSE_SYMBOL` — `NIFTY` or `BANKNIFTY`
- Leave Telegram/Ollama blank for now, fill in after steps 2 and 3 below.

## 2. Create your Telegram bot (free, ~2 minutes)

1. Open Telegram, search for **@BotFather**, send `/newbot`, follow prompts.
2. BotFather gives you a token like `123456:ABC-DEF...` → put it in `.env` as `TELEGRAM_BOT_TOKEN`.
3. Send any message to your new bot from your Telegram account.
4. In a browser, visit:
   `https://api.telegram.org/bot<YOUR_TOKEN>/getUpdates`
5. Find `"chat":{"id": 123456789 ...}` in the JSON → put that number in `.env` as `TELEGRAM_CHAT_ID`.

## 3. Install Ollama (free, local LLM)

**Windows shortcut:** run `scripts\setup_ollama.ps1` in PowerShell — it installs Ollama (via winget if available), waits for the service, pulls the model from your `.env`, and runs a test prompt, all in one go. If it succeeds, skip to step 4 below.

Manual steps:
1. Download and install from **https://ollama.com/download** (Windows/Mac/Linux installers available).
2. After install, Ollama runs as a background service on `http://localhost:11434` automatically.
3. Pull a model (choose one that fits your RAM — `llama3.1` needs ~8GB, `qwen2.5:3b` is lighter):
   ```bash
   ollama pull llama3.1
   ```
4. Quick test:
   ```bash
   ollama run llama3.1 "Say hello in one sentence."
   ```
5. In `.env`, set `OLLAMA_MODEL=llama3.1` (or whichever model you pulled).

If you'd rather skip Ollama initially, set `USE_OLLAMA=false` in `.env` — you'll
still get the full rule-based analysis, just without the LLM-written note.

## 4. Test one run manually

```bash
python main.py
```

You should see console output and (if configured) a Telegram message. If NSE
returns a 403/blocked error, wait a few seconds and re-run — NSE occasionally
rate-limits; the fetcher retries automatically but very frequent testing can
still trip it.

## 5. Schedule it to run every 5 minutes

The script does **one** fetch-analyze-notify cycle per run and exits (it
auto-skips outside market hours 9:15–15:30 IST, Mon–Fri), so use your OS
scheduler to trigger it every 5 minutes during the day.

### Linux / Mac (cron)
```bash
crontab -e
```
Add (adjust paths):
```
*/5 9-15 * * 1-5 cd /path/to/nse_trade_analyzer && /path/to/.venv/bin/python main.py >> logs.txt 2>&1
```

### Windows (Task Scheduler)
1. Open **Task Scheduler** → Create Task.
2. Trigger: Daily, repeat every 5 minutes, for a duration of 6 hours 15 minutes, starting 9:15 AM, Mon–Fri.
3. Action: Start a program →
   - Program: `C:\path\to\nse_trade_analyzer\.venv\Scripts\python.exe`
   - Arguments: `main.py`
   - Start in: `C:\path\to\nse_trade_analyzer`

## 6. Data

Each run appends a row to a local SQLite DB at `data/nse_analyzer.db`
(gitignored). Open it with any SQLite viewer (e.g. DB Browser for SQLite,
free) to see PCR/OI trends across the day.

---

## Project structure

| File | Purpose |
|---|---|
| `config.py` | Loads settings from `.env` |
| `nse_fetcher.py` | Pulls option-chain JSON from NSE with proper session/headers |
| `analysis.py` | Computes PCR, Max Pain, support/resistance, IV skew |
| `storage.py` | SQLite snapshot history |
| `ollama_client.py` | Sends metrics to local Ollama for a plain-English note |
| `telegram_notify.py` | Sends the formatted message to Telegram |
| `main.py` | Orchestrates one full cycle; entry point for the scheduler |

## Extending

- **More instruments**: loop `main.run_once()`-style logic over a list of symbols.
- **Price technicals**: add an `equity_fetcher.py` pulling NSE's quote API and compute RSI/VWAP/EMA with plain Python or `pandas`.
- **Dashboard**: `pip install streamlit` and build a small app reading from `data/nse_analyzer.db` — happy to build this next if useful.
- **Backtesting your rule logic**: since every snapshot is stored, you can replay `analysis.py` outputs against later price moves to see how predictive PCR/max-pain actually were for your instrument before trusting it live.

## Disclaimer

NSE data is provided for personal, non-commercial use per NSE's terms —
don't redistribute or resell it. This project is an analysis aid, not a
broker or execution system, and generates no buy/sell orders. Markets carry
risk; verify signals independently before acting on them.
