"""
Single-run entry point.

Design choice: rather than an internal infinite loop, this script does ONE
fetch-analyze-notify cycle and exits. You schedule it to run every 5 minutes
using cron (Linux/Mac) or Task Scheduler (Windows) — see README.md.
This is more robust than a long-running loop (no memory growth, easy to
restart, easy to inspect each run's logs independently).

It automatically no-ops outside NSE market hours (9:15-15:30 IST, Mon-Fri).
"""
import sys
from datetime import datetime, time as dtime

try:
    from zoneinfo import ZoneInfo
except ImportError:  # Python <3.9 fallback
    from backports.zoneinfo import ZoneInfo  # type: ignore

import config
from nse_fetcher import fetch_option_chain, NSEFetchError
from analysis import analyze_chain, rule_based_bias
from storage import init_db, save_snapshot, get_previous_snapshot
from telegram_notify import send_message

IST = ZoneInfo("Asia/Kolkata")


def is_market_open(now=None) -> bool:
    now = now or datetime.now(IST)
    if now.weekday() >= 5:  # Sat/Sun
        return False
    open_t = dtime(*config.MARKET_OPEN)
    close_t = dtime(*config.MARKET_CLOSE)
    return open_t <= now.time() <= close_t


def format_message(a, llm_note: str, prev: dict | None) -> str:
    oi_trend = ""
    if prev:
        d_call = a.total_call_oi - prev["total_call_oi"]
        d_put = a.total_put_oi - prev["total_put_oi"]
        oi_trend = f"\nΔCall OI: {d_call:+,} | ΔPut OI: {d_put:+,} (since last snapshot)"

    return (
        f"<b>{a.symbol} Option Chain — {datetime.now(IST).strftime('%H:%M:%S')} IST</b>\n"
        f"Spot: {a.underlying_value} | ATM: {a.atm_strike}\n"
        f"PCR(OI): {a.pcr_oi} | PCR(Vol): {a.pcr_volume}\n"
        f"Max Pain: {a.max_pain}\n"
        f"Resistance (Call OI): {a.top_resistance}\n"
        f"Support (Put OI): {a.top_support}\n"
        f"IV skew (Put-Call): {a.iv_skew}"
        f"{oi_trend}\n\n"
        f"<i>{llm_note}</i>\n\n"
        f"<i>Not financial advice — positioning read only.</i>"
    )


def run_once():
    if not is_market_open():
        print(f"[{datetime.now(IST)}] Market closed. Skipping run.")
        return

    init_db(config.DB_PATH)

    try:
        raw = fetch_option_chain(config.SYMBOL)
    except NSEFetchError as exc:
        print(f"[error] {exc}")
        send_message(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID,
                     f"⚠️ NSE fetch failed for {config.SYMBOL}: {exc}")
        return

    a = analyze_chain(raw, config.SYMBOL, config.STRIKE_RANGE)
    rule_note = rule_based_bias(a)

    if config.USE_OLLAMA:
        from ollama_client import get_trade_note
        llm_note = get_trade_note(a, rule_note, config.OLLAMA_HOST, config.OLLAMA_MODEL)
    else:
        llm_note = rule_note

    prev = get_previous_snapshot(config.DB_PATH, config.SYMBOL)
    save_snapshot(config.DB_PATH, a, llm_note)

    message = format_message(a, llm_note, prev)
    print(message)
    send_message(config.TELEGRAM_BOT_TOKEN, config.TELEGRAM_CHAT_ID, message)


if __name__ == "__main__":
    try:
        run_once()
    except Exception as exc:  # noqa: BLE001
        print(f"[fatal] {exc}", file=sys.stderr)
        sys.exit(1)
