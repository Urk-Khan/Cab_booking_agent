#!/usr/bin/env bash
# One-command project setup: creates venv, installs deps, prepares .env
set -e

cd "$(dirname "$0")"

PYTHON_BIN="${PYTHON_BIN:-python3.11}"
if ! command -v "$PYTHON_BIN" >/dev/null 2>&1; then
    echo "python3.11 not found, falling back to python3"
    PYTHON_BIN="python3"
fi

echo "Using $($PYTHON_BIN --version)"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    "$PYTHON_BIN" -m venv venv
fi

# shellcheck disable=SC1091
source venv/bin/activate

echo "Installing dependencies (this can take a few minutes)..."
pip install --upgrade pip >/dev/null
pip install -r requirements.txt

if [ ! -f ".env" ]; then
    cp .env.example .env
    echo ""
    echo "Created .env from .env.example — open it now and fill in your API keys"
    echo "(CARTESIA_API_KEY for STT+TTS, plus a key for whichever LLM_PROVIDER you pick)."
else
    echo ".env already exists, leaving it as-is."
fi

echo ""
echo "Setup complete. Next steps:"
echo "  1. source venv/bin/activate"
echo "  2. Edit .env with your API keys"
echo "  3. Run: python bot.py"
echo "  4. Expose it (e.g. 'ngrok http 7860') and point Telnyx at wss://<tunnel>/ws"
echo "     via a TeXML Bin — see README.md for exact steps."
