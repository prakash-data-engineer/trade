"""
Talks to a locally running Ollama server to turn computed option-chain
metrics into a short, plain-English positioning note.

This is NOT financial advice generation in the sense of "buy/sell X now" —
it's asked to describe positioning/bias based only on the numbers given,
and explicitly told to flag uncertainty. Treat its output as one input
among many, not a signal to trade on blindly.
"""
import requests

from analysis import ChainAnalysis

SYSTEM_PROMPT = (
    "You are a market-structure note writer. You are given computed options "
    "open-interest metrics for an Indian index (Nifty/BankNifty). Summarize "
    "the positioning in 3-4 concise sentences: overall bias implied by the "
    "data, key support/resistance zones, and any notable IV skew. "
    "Be neutral and analytical, not promotional. Do not tell the user to "
    "'buy' or 'sell' — describe what the data suggests and note that this "
    "is not financial advice and options positioning can shift quickly."
)


def build_prompt(a: ChainAnalysis, rule_note: str) -> str:
    return f"""
Symbol: {a.symbol}
Underlying value: {a.underlying_value}
ATM strike: {a.atm_strike}
PCR (OI): {a.pcr_oi}
PCR (Volume): {a.pcr_volume}
Max Pain: {a.max_pain}
Top resistance strikes (high call OI): {a.top_resistance}
Top support strikes (high put OI): {a.top_support}
Avg Call IV: {a.call_iv_avg}
Avg Put IV: {a.put_iv_avg}
IV skew (Put IV - Call IV): {a.iv_skew}
Rule-based read: {rule_note}

Write the positioning note now.
""".strip()


def get_trade_note(a: ChainAnalysis, rule_note: str, host: str, model: str, timeout: int = 30) -> str:
    prompt = build_prompt(a, rule_note)
    try:
        resp = requests.post(
            f"{host}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "stream": False,
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"].strip()
    except Exception as exc:  # noqa: BLE001
        return f"[Ollama unavailable, falling back to rule-based note] {rule_note} (error: {exc})"
