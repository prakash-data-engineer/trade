"""
Central configuration for the NSE trade analyzer.
Values are pulled from environment variables (see .env.example).
"""
import os
from dotenv import load_dotenv

load_dotenv()

# --- Instrument settings ---
SYMBOL = os.getenv("NSE_SYMBOL", "NIFTY")          # NIFTY or BANKNIFTY
STRIKE_RANGE = int(os.getenv("STRIKE_RANGE", "10"))  # strikes above/below ATM to analyze

# --- Telegram ---
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID", "")

# --- Ollama ---
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.1")
USE_OLLAMA = os.getenv("USE_OLLAMA", "true").lower() == "true"

# --- Storage ---
DB_PATH = os.getenv("DB_PATH", "data/nse_analyzer.db")

# --- Market hours (IST) ---
MARKET_OPEN = (9, 15)
MARKET_CLOSE = (15, 30)
