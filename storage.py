"""
Lightweight SQLite storage for option-chain analysis snapshots,
so you can track OI/PCR trends across the day (and over multiple days).
"""
import sqlite3
import os
from datetime import datetime

from analysis import ChainAnalysis


def _ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)


def init_db(db_path: str):
    _ensure_dir(db_path)
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS snapshots (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ts TEXT NOT NULL,
            symbol TEXT NOT NULL,
            underlying_value REAL,
            atm_strike REAL,
            pcr_oi REAL,
            pcr_volume REAL,
            max_pain REAL,
            top_resistance TEXT,
            top_support TEXT,
            call_iv_avg REAL,
            put_iv_avg REAL,
            iv_skew REAL,
            total_call_oi INTEGER,
            total_put_oi INTEGER,
            llm_note TEXT
        )
        """
    )
    conn.commit()
    conn.close()


def save_snapshot(db_path: str, a: ChainAnalysis, llm_note: str = ""):
    conn = sqlite3.connect(db_path)
    conn.execute(
        """
        INSERT INTO snapshots (
            ts, symbol, underlying_value, atm_strike, pcr_oi, pcr_volume,
            max_pain, top_resistance, top_support, call_iv_avg, put_iv_avg,
            iv_skew, total_call_oi, total_put_oi, llm_note
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            datetime.now().isoformat(timespec="seconds"),
            a.symbol,
            a.underlying_value,
            a.atm_strike,
            a.pcr_oi,
            a.pcr_volume,
            a.max_pain,
            ",".join(str(s) for s in a.top_resistance),
            ",".join(str(s) for s in a.top_support),
            a.call_iv_avg,
            a.put_iv_avg,
            a.iv_skew,
            a.total_call_oi,
            a.total_put_oi,
            llm_note,
        ),
    )
    conn.commit()
    conn.close()


def get_previous_snapshot(db_path: str, symbol: str):
    """Returns the most recent prior snapshot row for the symbol, or None."""
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    cur = conn.execute(
        "SELECT * FROM snapshots WHERE symbol = ? ORDER BY id DESC LIMIT 1",
        (symbol,),
    )
    row = cur.fetchone()
    conn.close()
    return dict(row) if row else None
