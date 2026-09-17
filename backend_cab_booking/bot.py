"""
Ashad — Pipecat voice pipeline (pipecat-ai 1.8.1 API).

Cascade pipeline: Telnyx audio in -> STT -> LLM (English-only, with booking tools) -> TTS ->
Telnyx audio out. STT and TTS always use Cartesia. The LLM provider is picked at runtime
from .env (LLM_PROVIDER) — Anthropic or OpenAI — both cloud APIs, both requiring an
API key.

Run with:
    python bot.py

This uses Pipecat's built-in runner (`pipecat.runner.run.main()`), which starts its own
FastAPI/uvicorn server (default: http://localhost:7860) and serves the Telnyx WebSocket at
/ws. There's no separate server.py in this version — the runner IS the server.

Telnyx setup differs from older Pipecat versions too: instead of a webhook that returns
TeXML dynamically, you paste a small static TeXML snippet into a "TeXML Bin" in the Telnyx
portal (pointing at your ngrok/production wss:// URL), then assign a TeXML Application using
that Bin to your phone number. See README.md for exact steps.

Everything downstream of the LLM's tool calls (Supabase bookings/customers, Telnyx SMS,
Google Places) is called directly — see tools.py for the handlers this pipeline calls.
"""

import os
import sys
import socket
import time

# Force IPv4 socket resolution on Windows to avoid AWS/Cartesia WebSocket handshake timeouts
_orig_getaddrinfo = socket.getaddrinfo
def _ipv4_getaddrinfo(host, port, family=0, type=0, proto=0, flags=0):
    return _orig_getaddrinfo(host, port, socket.AF_INET, type, proto, flags)
socket.getaddrinfo = _ipv4_getaddrinfo

if sys.platform == "win32":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from dotenv import load_dotenv
from loguru import logger
from pipecat.audio.vad.silero import SileroVADAnalyzer
from pipecat.audio.vad.vad_analyzer import VADParams
from pipecat.frames.frames import TTSSpeakFrame
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.worker import PipelineParams, PipelineWorker
from pipecat.processors.aggregators.llm_context import LLMContext
from pipecat.processors.aggregators.llm_response_universal import (
    LLMContextAggregatorPair,
    LLMUserAggregatorParams,
)
from pipecat.runner.types import RunnerArguments
from pipecat.runner.utils import create_transport
from pipecat.transports.base_transport import BaseTransport
from pipecat.transports.websocket.fastapi import FastAPIWebsocketParams
from pipecat.workers.runner import WorkerRunner

from prompts import CAB_BOOKING_SYSTEM_PROMPT, GREETING_EN
from tools import CAB_BOOKING_TOOLS

load_dotenv(override=True)

# Warm the Silero VAD model once, when the server process starts, instead of paying that
# cost on every call. SileroVADAnalyzer.__init__ imports onnxruntime and reads the bundled
# .onnx model file off disk — real work, not free. Each call still builds its own
# SileroVADAnalyzer below (VAD state — rolling buffers, confidence tracking — must stay
# isolated per call: https://github.com/pipecat-ai/pipecat/issues/2050), so this doesn't
# remove per-call construction entirely. It does mean the one-time costs (importing
# onnxruntime, the first disk read of the model file) happen at boot, off the call's
# critical path, so every real call's SileroVADAnalyzer() is cheaper than the very first one
# would otherwise have been.
_vad_warmup_start = time.monotonic()
SileroVADAnalyzer()
logger.info(f"Silero VAD warmed at server startup in {time.monotonic() - _vad_warmup_start:.2f}s")


# =============================================================================
# 1. SPEECH-TO-TEXT (STT) SERVICE BUILDER
# =============================================================================
def _build_stt_service():
    """Builds the STT service. Cartesia only (Ink-Whisper), requires CARTESIA_API_KEY."""
    from pipecat.services.cartesia.stt import CartesiaSTTService

    api_key = os.getenv("CARTESIA_API_KEY")
    if not api_key:
        raise ValueError("CARTESIA_API_KEY is not set in .env")

    return CartesiaSTTService(api_key=api_key)


# =============================================================================
# 2. LARGE LANGUAGE MODEL (LLM) SERVICE BUILDER
# =============================================================================
def _build_llm_service():
    """Builds the LLM service based on LLM_PROVIDER in .env. All options are cloud APIs
    that require a key:
    - 'openai': GPT models via OpenAI (requires OPENAI_API_KEY)
    - 'anthropic': Claude Sonnet (requires ANTHROPIC_API_KEY)
    """
    provider = os.getenv("LLM_PROVIDER", "openai").lower()

    if provider == "anthropic":
        from pipecat.services.anthropic.llm import AnthropicLLMService

        return AnthropicLLMService(
            api_key=os.getenv("ANTHROPIC_API_KEY"),
            settings=AnthropicLLMService.Settings(
                model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-6"),
                system_instruction=CAB_BOOKING_SYSTEM_PROMPT,
                # The system prompt + all 16 tool schemas (~2-3k tokens) would otherwise be
                # re-sent as fresh, full-price input tokens on every single LLM call for every
                # turn of every call. This turns on Anthropic's prompt caching: Pipecat's
                # adapter auto-places cache_control breakpoints on the system prompt, tools,
                # and prior turns, so anything unchanged since the last turn is billed at
                # ~10% of normal input cost AND is read from cache instead of reprocessed —
                # cutting cost and shaving latency off every turn after the first.
                enable_prompt_caching=True,
                # Voice replies are meant to be 1-2 sentences (see prompts.py). Without an
                # explicit cap the model can ramble past that, burning completion tokens and
                # adding TTS delay. 200 tokens is generous headroom for 1-2 spoken sentences.
                max_tokens=200,
            ),
        )

    elif provider == "openai":
        from pipecat.services.openai.llm import OpenAILLMService

        return OpenAILLMService(
            api_key=os.getenv("OPENAI_API_KEY"),
            settings=OpenAILLMService.Settings(
                model=os.getenv("OPENAI_MODEL", "gpt-5.4-2026-03-05"),
                system_instruction=CAB_BOOKING_SYSTEM_PROMPT,
                # OpenAI caches automatically (no flag needed) once a prompt exceeds ~1024
                # tokens, which your system prompt + tool schemas already do. Just cap
                # completion length the same way, for the same reason as the Anthropic branch.
                # gpt-5.x (reasoning-family) models reject the older `max_tokens` param and
                # require `max_completion_tokens` instead — using the wrong one 400s the call.
                max_completion_tokens=200,
            ),
        )

    else:
        raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")


# =============================================================================
# 3. TEXT-TO-SPEECH (TTS) SERVICE BUILDER
# =============================================================================
def _build_tts_service():
    """Builds the TTS service. Cartesia only (Sonic), requires CARTESIA_API_KEY."""
    from pipecat.services.cartesia.tts import CartesiaTTSService

    api_key = os.getenv("CARTESIA_API_KEY")
    if not api_key:
        raise ValueError("CARTESIA_API_KEY is not set in .env")

    return CartesiaTTSService(
        api_key=api_key,
        settings=CartesiaTTSService.Settings(
            voice=os.getenv("CARTESIA_VOICE_ID", "86e30c1d-714b-4074-a1f2-1cb6b552fb49"),
        ),
    )


# =============================================================================
# 4. MAIN PIPELINE SESSION RUNNER
# =============================================================================
async def run_bot(transport: BaseTransport, runner_args: RunnerArguments) -> None:
    """Run the voice bot for one incoming call session."""
    call_start = time.monotonic()
    logger.info("Starting Ashad Session")

    stt = _build_stt_service()
    tts = _build_tts_service()
    llm = _build_llm_service()

    # Log exactly when each Cartesia WebSocket finishes connecting, with elapsed time since
    # this call started. This is the concrete way to find out how much of your 15-20s is
    # actually Cartesia's handshake (normally well under a second) versus everything else in
    # the chain (Telnyx/TeXML setup, ngrok, cold LLM call, VAD). Don't guess — read these logs.
    @stt.event_handler("on_connected")
    async def on_stt_connected(service):
        logger.info(f"Cartesia STT connected — {time.monotonic() - call_start:.2f}s into call")

    @tts.event_handler("on_connected")
    async def on_tts_connected(service):
        logger.info(f"Cartesia TTS connected — {time.monotonic() - call_start:.2f}s into call")

    # VAD configuration tuned to ignore background speech & ambient room noise
    vad_params = VADParams(
        confidence=0.85,   # Higher confidence threshold: ignores faint background voices
        min_volume=0.70,   # Volume threshold: filters out low-volume room noise and fan hums
        start_secs=0.20,   # Requires 200ms of sustained speech to avoid clicks
        stop_secs=0.35,    # Ends turn 350ms after user finishes speaking (snappy responses)
    )

    context = LLMContext(tools=CAB_BOOKING_TOOLS)
    user_aggregator, assistant_aggregator = LLMContextAggregatorPair(
        context,
        user_params=LLMUserAggregatorParams(
            vad_analyzer=SileroVADAnalyzer(params=vad_params),
            user_turn_stop_timeout=0.35,
        ),
    )

    pipeline = Pipeline(
        [
            transport.input(),
            stt,
            user_aggregator,
            llm,
            tts,
            transport.output(),
            assistant_aggregator,
        ]
    )

    call_data = runner_args.call_data
    caller_phone = call_data.from_number if call_data else None

    worker = PipelineWorker(
        pipeline,
        params=PipelineParams(
            enable_metrics=True,
            enable_usage_metrics=True,
            audio_in_sample_rate=8000,   # Telnyx PSTN audio is 8kHz
            audio_out_sample_rate=8000,
        ),
        app_resources={"caller_phone": caller_phone, "session_id": runner_args.session_id},
    )

    @transport.event_handler("on_client_connected")
    async def on_client_connected(transport, client):
        logger.info(
            f"Call connected, caller={caller_phone} — {time.monotonic() - call_start:.2f}s "
            "into call"
        )
        # Speak the greeting directly, skipping the LLM entirely for this first turn.
        # Previously this pushed an LLMRunFrame and waited for a full LLM completion before
        # TTS could even start — an extra network round-trip the caller sat through in
        # silence. TTSSpeakFrame goes straight to the TTS service, so the greeting starts
        # playing immediately. append_to_context defaults to True (Pipecat >=1.4), so it's
        # still recorded in the conversation history for later turns exactly like before.
        await tts.queue_frame(TTSSpeakFrame(GREETING_EN))
        logger.info(f"Greeting queued to TTS — {time.monotonic() - call_start:.2f}s into call")

    @transport.event_handler("on_client_disconnected")
    async def on_client_disconnected(transport, client):
        logger.info("Call ended")
        await worker.cancel()

    runner = WorkerRunner(handle_sigint=False)
    await runner.add_workers(worker)
    await runner.run()


async def bot(runner_args: RunnerArguments):
    """Entry point the Pipecat runner calls for each new connection."""
    supabase_url = os.getenv("SUPABASE_URL", "")
    supabase_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
    if not supabase_url or not supabase_key:
        logger.warning(
            "SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY are not set in .env. Every booking "
            "tool call (create_booking, view_booking, etc.) will fail instantly, forcing "
            "extra apology+retry turns that make the call feel much slower. Run "
            "icabbi_taxi_schema.sql in your Supabase project's SQL Editor, then set both "
            "values from Project Settings -> API."
        )

    transport_params = {
        "telnyx": lambda: FastAPIWebsocketParams(audio_in_enabled=True, audio_out_enabled=True),
    }

    transport = await create_transport(runner_args, transport_params)

    call_data = runner_args.call_data
    if call_data:
        logger.info(f"From number: {call_data.from_number}")

    await run_bot(transport, runner_args)


if __name__ == "__main__":
    from pipecat.runner.run import main

    main()