@echo off
REM ============================================================
REM  start_bot.bat — One-Click Ashad Voice Agent Launcher
REM  Automatically sets up Cloudflare tunnel, updates Telnyx,
REM  and starts the voice bot with Cartesia STT + TTS.
REM ============================================================

cd /d "%~dp0"
if exist venv\Scripts\activate.bat call venv\Scripts\activate.bat
python start_agent.py
if errorlevel 1 py start_agent.py
pause
