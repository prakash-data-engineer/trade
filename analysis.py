"""
Computes analytics from a raw NSE option-chain JSON payload:
- ATM strike
- Put-Call Ratio (PCR) by OI
- Max Pain
- Support/Resistance from top OI strikes
- IV skew (avg call IV vs avg put IV near ATM)
- OI change since last snapshot (call vs put buildup)
"""
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ChainAnalysis:
    symbol: str
    underlying_value: float
    atm_strike: float
    pcr_oi: float
    pcr_volume: float
    max_pain: float
    top_resistance: list = field(default_factory=list)  # highest call OI strikes
    top_support: list = field(default_factory=list)      # highest put OI strikes
    call_iv_avg: Optional[float] = None
    put_iv_avg: Optional[float] = None
    iv_skew: Optional[float] = None
    total_call_oi: int = 0
    total_put_oi: int = 0


def _nearest_strike(strikes, value):
    return min(strikes, key=lambda s: abs(s - value))


def analyze_chain(raw: dict, symbol: str, strike_range: int = 10) -> ChainAnalysis:
    records = raw["records"]
    underlying_value = records["underlyingValue"]
    all_data = records["data"]

    strikes = sorted({row["strikePrice"] for row in all_data})
    atm_strike = _nearest_strike(strikes, underlying_value)
    atm_index = strikes.index(atm_strike)
    lo = max(0, atm_index - strike_range)
    hi = min(len(strikes), atm_index + strike_range + 1)
    window_strikes = set(strikes[lo:hi])

    call_oi_by_strike = {}
    put_oi_by_strike = {}
    call_vol_total = 0
    put_vol_total = 0
    call_iv_vals = []
    put_iv_vals = []

    for row in all_data:
        sp = row["strikePrice"]
        if sp not in window_strikes:
            continue
        ce = row.get("CE")
        pe = row.get("PE")
        if ce:
            call_oi_by_strike[sp] = ce.get("openInterest", 0)
            call_vol_total += ce.get("totalTradedVolume", 0) or 0
            if ce.get("impliedVolatility"):
                call_iv_vals.append(ce["impliedVolatility"])
        if pe:
            put_oi_by_strike[sp] = pe.get("openInterest", 0)
            put_vol_total += pe.get("totalTradedVolume", 0) or 0
            if pe.get("impliedVolatility"):
                put_iv_vals.append(pe["impliedVolatility"])

    total_call_oi = sum(call_oi_by_strike.values())
    total_put_oi = sum(put_oi_by_strike.values())

    pcr_oi = round(total_put_oi / total_call_oi, 3) if total_call_oi else 0.0
    pcr_volume = round(put_vol_total / call_vol_total, 3) if call_vol_total else 0.0

    # Max pain: strike where total option-writer loss is minimized
    max_pain_strike = None
    min_loss = None
    for candidate in window_strikes:
        loss = 0
        for sp, oi in call_oi_by_strike.items():
            if candidate > sp:
                loss += (candidate - sp) * oi
        for sp, oi in put_oi_by_strike.items():
            if candidate < sp:
                loss += (sp - candidate) * oi
        if min_loss is None or loss < min_loss:
            min_loss = loss
            max_pain_strike = candidate

    top_resistance = sorted(call_oi_by_strike.items(), key=lambda x: -x[1])[:3]
    top_support = sorted(put_oi_by_strike.items(), key=lambda x: -x[1])[:3]

    call_iv_avg = round(sum(call_iv_vals) / len(call_iv_vals), 2) if call_iv_vals else None
    put_iv_avg = round(sum(put_iv_vals) / len(put_iv_vals), 2) if put_iv_vals else None
    iv_skew = round(put_iv_avg - call_iv_avg, 2) if call_iv_avg and put_iv_avg else None

    return ChainAnalysis(
        symbol=symbol,
        underlying_value=underlying_value,
        atm_strike=atm_strike,
        pcr_oi=pcr_oi,
        pcr_volume=pcr_volume,
        max_pain=max_pain_strike,
        top_resistance=[s for s, _ in top_resistance],
        top_support=[s for s, _ in top_support],
        call_iv_avg=call_iv_avg,
        put_iv_avg=put_iv_avg,
        iv_skew=iv_skew,
        total_call_oi=total_call_oi,
        total_put_oi=total_put_oi,
    )


def rule_based_bias(a: ChainAnalysis) -> str:
    """
    Simple, transparent heuristic bias — used as a fallback if Ollama
    is unavailable, and also as a sanity check alongside the LLM output.
    Not financial advice; purely a reading of OI/PCR positioning.
    """
    notes = []
    if a.pcr_oi > 1.2:
        notes.append("PCR > 1.2 suggests put-heavy positioning (often read as bullish/support-building).")
    elif a.pcr_oi < 0.8:
        notes.append("PCR < 0.8 suggests call-heavy positioning (often read as bearish/resistance-building).")
    else:
        notes.append("PCR near 1.0 suggests a relatively balanced/neutral positioning.")

    if a.top_resistance:
        notes.append(f"Highest call OI (resistance zone) near {a.top_resistance[0]}.")
    if a.top_support:
        notes.append(f"Highest put OI (support zone) near {a.top_support[0]}.")
    if a.iv_skew is not None:
        if a.iv_skew > 1:
            notes.append(f"Put IV > Call IV by {a.iv_skew} pts (downside hedging demand).")
        elif a.iv_skew < -1:
            notes.append(f"Call IV > Put IV by {abs(a.iv_skew)} pts (upside speculation demand).")

    return " ".join(notes)
