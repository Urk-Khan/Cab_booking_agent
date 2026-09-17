# Ashad Voice Agent — Architecture, Execution Flow & Log Analysis

This document explains step-by-step how the voice pipeline processes a real phone call from the moment a caller dials the Telnyx number to the final speech output.

> **Note:** the trace and timings below are from an earlier run made with `LLM_PROVIDER=groq`.
> The project's default LLM provider is now `openai` (see `.env` / `README.md`), so step 5 in
> the diagram and the "LLM Inference" numbers reflect the old Groq setup rather than the
> current OpenAI-based configuration. The rest of the pipeline (Telnyx, Cartesia STT/TTS) is
> unchanged.

---

## 1. High-Level Architecture

```
[ Mobile Phone ] (e.g., +1 917-795-4404)
       │
       │ (PSTN Call)
       ▼
[ Telnyx Phone Number ] (+1 855-501-0702)
       │
       │ HTTP POST / (Fetches TeXML Stream)
       ▼
[ Cloudflare Tunnel / Public Proxy ]
       │
       │ WebSocket (wss://.../ws, 8kHz PCMU Audio)
       ▼
[ bot.py — Pipecat Pipeline Server (Port 7860) ]
       │
       ├── 1. FastAPIWebsocketInputTransport (Receives audio chunks from Telnyx)
       ├── 2. Silero VAD & SmartTurn (Detects when user starts/stops speaking)
       ├── 3. CartesiaSTTService (Ink-Whisper: transcribes speech via Cartesia's cloud API)
       ├── 4. LLMUserAggregator (Gathers transcripts into conversation context)
       ├── 5. GroqLLMService (openai/gpt-oss-20b: decides reply & tool calls)
       ├── 6. CartesiaTTSService (Sonic: converts text back to speech audio via Cartesia's cloud API)
       ├── 7. FastAPIWebsocketOutputTransport (Encodes to 8kHz PCMU audio)
       └── 8. TelnyxFrameSerializer (Streams audio packets back to caller's ear)
```

---

## 2. Step-by-Step Execution Lifecycle

### Step 1: Call Ingestion & TeXML Handshake
1. A caller dials **`+1 855-501-0702`**.
2. Telnyx makes an HTTP `POST /` to your public URL.
3. `bot.py` immediately responds with standard TeXML:
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
     <Connect>
       <Stream url="wss://physically-varies-collapse-while.trycloudflare.com/ws" bidirectionalMode="rtp"></Stream>
     </Connect>
   </Response>
   ```
4. Telnyx opens a bidirectional WebSocket at `/ws` sending raw **8,000 Hz PCMU (µ-law)** telephony audio packets.

---

### Step 2: Session Initialization & Greeting Trigger
1. `bot.py` registers the caller's phone number (`+19177954404`) and assigns a unique `session_id`.
2. The `on_client_connected` event fires:
   - Injects a system instruction into `LLMContext`: `"[Call connected. Greet the caller warmly...]"`
   - Queues an `LLMRunFrame()` to trigger the opening line immediately.

---

### Step 3: Speech Generation (LLM + TTS)
1. **LLM (Groq - `openai/gpt-oss-20b`):**
   - Receives the conversation history and system prompt.
   - Generates the text: `"Thank you for calling, aap ka naam kya hai?"`
2. **TTS (Cartesia - Sonic):**
   - Synthesizes the text into audio via Cartesia's cloud API.
   - The transport resamples the audio down to 8 kHz PCMU and streams it back over the WebSocket to Telnyx.
3. The caller hears the greeting on their phone.

---

### Step 4: Voice Activity Detection (VAD) & Smart Turn Taking
1. While the caller listens or speaks, **Silero VAD** monitors incoming audio frames.
2. When the caller starts speaking:
   - `_on_user_turn_started`: VAD detects energy above the threshold.
   - If the bot was currently speaking, an `InterruptionFrame` is broadcast to immediately mute bot playback (barge-in support).
3. When the caller finishes speaking:
   - **SmartTurn (v3.2)** analyzes the acoustic pause and semantic completeness.
   - Once silence reaches the threshold, it marks `EndOfTurnState.COMPLETE`.

---

### Step 5: Speech-to-Text (Cartesia)
1. The recorded audio slice is passed to **`CartesiaSTTService`** (Ink-Whisper, cloud).
2. The model transcribes the user's speech into text (e.g. name, location, or request).
3. The transcription is pushed into `LLMUserAggregator`.

---

### Step 6: Tool Execution & Multi-Turn Conversation
1. The LLM evaluates the user's text against the cab booking system prompt.
2. If all details (Name, Pickup, Dropoff, Time) are gathered and confirmed:
   - The LLM outputs a function call: `create_booking(...)`.
   - `tools.py` writes the booking straight to Supabase via `booking_db.py`.
   - Tool results return back to the LLM to confirm the booking reference over the phone.
3. The cycle repeats seamlessly until the call is completed or transferred.

---

## 3. Log Walkthrough & Interpretation

Here is the explanation of the actual lines from your terminal output:

### 1. The Bot Synthesizes & Speaks the Greeting:
```text
GroqLLMService#0 processing time: 1.778s
CartesiaTTSService#1: Generating TTS [Thank you for calling, aap ka naam kya hai?]
CartesiaTTSService#1 TTFB: 0.150s
CartesiaTTSService#1: Finished TTS [Thank you for calling, aap ka naam kya hai?]
pipecat.transports.base_output:_bot_started_speaking:706 - Bot started speaking
```
* **Meaning:** Groq generated the greeting, Cartesia synthesized it in about **0.15 seconds (TTFB - Time To First Byte)**, and Telnyx started playing the voice into your ear.

---

### 2. The Bot Finishes Speaking:
```text
pipecat.transports.base_output:_bot_stopped_speaking:758 - Bot stopped speaking
```
* **Meaning:** The greeting finished playing after ~3.0 seconds, and the bot transitioned to active listening mode.

---

### 3. You Started Speaking (VAD Detection):
```text
LLMUserAggregator#0: User started speaking (strategy: VADUserTurnStartStrategy#0)
CartesiaSTTService#1 usage audio seconds: 2.180
CartesiaSTTService#1 processing time: 0.210s
End of Turn result: EndOfTurnState.COMPLETE
```
* **Meaning:** 
  * Silero VAD detected your voice.
  * You spoke for **2.18 seconds**.
  * Cartesia transcribed your audio via its cloud API in about **0.21 seconds**.
  * SmartTurn confirmed your sentence was complete (`COMPLETE`).

---

### 4. Turn Processing & Call Termination:
```text
Call ended
Pipeline worker PipelineWorker#0 has finished
WorkerRunner finished running
```
* **Meaning:** When you hung up, Telnyx sent a WebSocket close frame, triggering a graceful pipeline teardown and resource cleanup.

---

## 4. Key Metrics Reference

| Metric | What It Measures | Typical Value in Current Setup |
|---|---|---|
| **STT Processing Time** | Time taken by Cartesia (cloud) to transcribe speech | ~0.15s – 0.25s |
| **TTS TTFB** | Time To First Byte (audio synthesis latency) | ~0.10s – 0.20s |
| **LLM Inference** | Time for Groq (`openai/gpt-oss-20b`) to return response | ~0.8s – 1.7s |
| **PSTN Audio Quality** | Telnyx sample rate & codec | 8,000 Hz PCMU (G.711u) |
