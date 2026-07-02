"""
Fetches live option-chain data from NSE's public (unofficial) JSON API.

NSE blocks plain requests without browser-like headers and valid cookies,
so we first hit the homepage to collect cookies, then call the API endpoint
using the same session.
"""
import time
import requests

BASE_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept": "*/*",
    "Referer": "https://www.nseindia.com/option-chain",
}

HOME_URL = "https://www.nseindia.com/option-chain"
INDEX_API_URL = "https://www.nseindia.com/api/option-chain-indices?symbol={symbol}"


class NSEFetchError(Exception):
    pass


def _new_session() -> requests.Session:
    session = requests.Session()
    session.headers.update(BASE_HEADERS)
    # Warm up: visiting the homepage sets the cookies the API expects.
    resp = session.get(HOME_URL, timeout=10)
    if resp.status_code != 200:
        raise NSEFetchError(f"Failed to warm up NSE session: {resp.status_code}")
    return session


def fetch_option_chain(symbol: str, retries: int = 3, delay: float = 2.0) -> dict:
    """
    Returns the raw JSON payload from NSE's option-chain-indices API
    for the given symbol (e.g. NIFTY, BANKNIFTY).
    """
    last_err = None
    for attempt in range(1, retries + 1):
        try:
            session = _new_session()
            url = INDEX_API_URL.format(symbol=symbol.upper())
            resp = session.get(url, timeout=10)
            if resp.status_code == 200:
                return resp.json()
            last_err = f"HTTP {resp.status_code}"
        except Exception as exc:  # noqa: BLE001
            last_err = str(exc)
        time.sleep(delay * attempt)  # backoff
    raise NSEFetchError(f"Could not fetch option chain for {symbol} after {retries} attempts: {last_err}")


if __name__ == "__main__":
    import json
    data = fetch_option_chain("NIFTY")
    print(json.dumps(data, indent=2)[:1000])
