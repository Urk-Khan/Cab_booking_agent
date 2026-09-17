# Provider Configuration & Audio Optimization Guide

This guide explains:
1. How background voice & noise filtering works.
2. The provider setup: Cartesia for STT + TTS, and your choice of LLM API.
3. The exact `.env` configuration.

---

## 1. Background Noise & Echo Filtering

In [bot.py](bot.py), the Silero Voice Activity Detector (VAD) is configured to filter out background chatter and room echoes:

```python
vad_params = VADParams(
    confidence=0.85,   # Higher threshold: only activates for clear, direct speech (ignores background chatter)
    min_volume=0.70,   # Volume threshold: filters out quiet room noise, fan hums, and speaker bleed
    start_secs=0.20,   # Requires 200ms of sustained speech to avoid clicks/coughs
    stop_secs=0.35,    # Triggers response 350ms after you stop speaking (eliminates awkward pauses)
)
```

---

## 2. Providers

STT and TTS are both fixed to **Cartesia** (Ink-Whisper for STT, Sonic for TTS — high
accuracy, ~100ms TTS latency). The LLM is the only stage you pick, via `LLM_PROVIDER`.

```env
# STT + TTS (Cartesia — one key covers both)
STT_PROVIDER=cartesia
TTS_PROVIDER=cartesia
CARTESIA_API_KEY=your_cartesia_api_key
CARTESIA_VOICE_ID=12e85709-099c-480a-ba3e-875c41a9611a

# LLM — pick one:
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-5.4-2026-03-05

# LLM_PROVIDER=anthropic
# ANTHROPIC_API_KEY=your_anthropic_api_key
# ANTHROPIC_MODEL=claude-sonnet-4-6
```

---

## 3. How the Code Picks Providers

In [bot.py](bot.py), the service builders read `.env` at runtime:

- `_build_stt_service()` — always builds `CartesiaSTTService` from `CARTESIA_API_KEY`.
- `_build_tts_service()` — always builds `CartesiaTTSService` from `CARTESIA_API_KEY` /
  `CARTESIA_VOICE_ID`.
- `_build_llm_service()` checks `LLM_PROVIDER`: `openai` or `anthropic`.

---

## 4. How to Run

1. Make sure your `.env` has `CARTESIA_API_KEY` and a key for your chosen `LLM_PROVIDER`.
2. In PowerShell terminal:
   ```powershell
   python bot.py -t telnyx -x physically-varies-collapse-while.trycloudflare.com
   ```
3. Dial **`+1 855-501-0702`**.
