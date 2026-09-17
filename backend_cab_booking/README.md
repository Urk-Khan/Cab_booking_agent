# Ashad — Pipecat Voice Agent (Cab Booking)

Self-hosted, English-only inbound voice agent for phone-based cab booking, built
on Pipecat 1.8.1. Every downstream integration is called directly from the pipeline —
no workflow tool, no webhooks to stand up separately:

- **Supabase** — bookings, customers, vehicles, drivers, dispatch/fare/call history
- **Google Places API (New)** — resolves pickup/drop-off locations, US-only
- **Telnyx** — the call itself, plus booking-confirmation SMS

```
Telnyx call → bot.py (Pipecat's built-in runner, serves /ws) → cascade pipeline
                                                                     │
                                             STT → LLM (tools) → TTS
                                                                     │
                          tools.py → booking_db.py → Supabase (bookings/customers/...)
                                   → places.py → Google Places API
                                   → Telnyx Messaging API (SMS)
```

## Files

| File | Purpose |
|---|---|
| `bot.py` | Everything: builds the pipeline AND runs the server (Pipecat's built-in runner) |
| `prompts.py` | English-only system prompt |
| `tools.py` | LLM tools — plain async functions with docstrings, auto-turned into schemas by Pipecat |
| `booking_db.py` | Pure data layer — bookings/customers/vehicles/drivers/dispatch/fare quotes, straight to Supabase |
| `supabase_client.py` | Cached Supabase client (service role key) |
| `places.py` | Google Places API (New) lookup — US-only filtering, "precise enough to confirm" check |
| `icabbi_taxi_schema.sql` | Run this once in your Supabase project's SQL Editor |
| `test_console_chat.py` | Plain-text chat with the LLM, no audio/Telnyx needed |
| `.env.example` | All required environment variables |

There's no separate `server.py` in this version — `python bot.py` starts Pipecat's built-in
dev server (FastAPI/uvicorn under the hood) and serves the Telnyx WebSocket at `/ws` itself.

## 1. Install

```bash
./setup.sh          # Linux/macOS — creates venv, installs deps, copies .env.example
source venv/bin/activate
```

On Windows PowerShell, do this instead:
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
pip install --upgrade pip
pip install -r requirements.txt
Copy-Item .env.example .env
```

## 2. Set up Supabase

1. Create a project at [supabase.com](https://supabase.com) if you don't have one yet.
2. Open **SQL Editor** in your project and run `icabbi_taxi_schema.sql` from this repo —
   creates `customers`, `vehicles`, `drivers`, `bookings`, `booking_status_history`,
   `call_logs`, `fare_quotes`, `dispatch_history`, and two convenience views.
3. In **Project Settings → API**, copy the Project URL and the **service_role** key (not the
   anon key — the service role key bypasses Row Level Security, which is what lets the
   backend read/write freely) into `.env` as `SUPABASE_URL` and `SUPABASE_SERVICE_ROLE_KEY`.

## 3. Fill in the rest of `.env`

| Stage | Provider | Key(s) |
|---|---|---|
| STT | Cartesia (Ink-Whisper) | `CARTESIA_API_KEY` |
| TTS | Cartesia (Sonic) | `CARTESIA_API_KEY` (same key as STT) |
| LLM | pick one via `LLM_PROVIDER`: `openai` / `anthropic` | `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` |
| Location lookup | Google Places API (New) | `GOOGLE_MAPS_API_KEY` |
| Database | Supabase | `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY` |
| Call + SMS | Telnyx | `TELNYX_API_KEY`, `TELNYX_ACCOUNT_SID`, `TELNYX_SMS_FROM_NUMBER` |

`TELNYX_SMS_FROM_NUMBER` needs to be a Telnyx number enabled on a **messaging profile** —
this is what `send_confirmation` in `tools.py` texts from.

## 4. Test without any phone number at all

```bash
python test_console_chat.py
```

Plain-text chat with Ashad in your terminal — validates your LLM provider and the system
prompt before touching audio or Telnyx. This script doesn't wire up tool calling, so it
won't exercise Supabase/Places/Telnyx — for that, run the full bot (step 6) and call it, or
call the pipeline's tool functions directly in a scratch script.

## 5. Run the bot

```bash
python bot.py
```

This starts Pipecat's runner on `http://localhost:7860` and serves the Telnyx media stream
at `ws://localhost:7860/ws`. If `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` aren't set,
you'll see a warning at startup — every booking tool call will fail until they are.

## 6. Connect a real Telnyx number

Telnyx's setup for this Pipecat version uses a **TeXML Bin** (a static XML snippet you paste
into the portal) rather than a webhook that returns TeXML dynamically:

1. **Buy a number** — [Telnyx Portal → Numbers → Buy Numbers](https://portal.telnyx.com/#/numbers/buy-numbers). A US number activates faster than others for testing, and matches the US-only service area in the prompt.
2. **Expose your local server**: `ngrok http 7860`, copy the `https://xxxxx.ngrok-free.app` URL.
3. **Create a TeXML Bin** — [Portal → Call Control → TeXML Bin](https://portal.telnyx.com/#/call-control/texml-bin) → "Create new TeXML Bin". Leave URL blank. Paste this into Content (swap in your ngrok host):
   ```xml
   <?xml version="1.0" encoding="UTF-8"?>
   <Response>
     <Connect>
       <Stream url="wss://xxxxx.ngrok-free.app/ws" bidirectionalMode="rtp"></Stream>
     </Connect>
   </Response>
   ```
4. **Create a TeXML Application** — [Portal → Call Control → TeXML](https://portal.telnyx.com/#/call-control/texml) → new app → under Webhooks set Voice Method to POST, Webhook URL Method to "TeXML Bin URL", and select the Bin from step 3.
5. **Assign the app to your number** — [Portal → Numbers → My Numbers](https://portal.telnyx.com/#/numbers/my-numbers) → edit your number → select the TeXML Application from step 4.
6. **Enable messaging for `TELNYX_SMS_FROM_NUMBER`** — [Portal → Messaging → Messaging Profiles](https://portal.telnyx.com/#/messaging/messaging-profiles), attach your number so `send_confirmation` can text from it.
7. **Call the number.** Watch the `python bot.py` terminal for logs.

Every time you restart `ngrok`, you get a new subdomain — update the TeXML Bin's Content
(step 3) with the new URL, or the call will fail silently.

## 7. What each tool call touches

| Tool | Backend |
|---|---|
| `create_booking`, `view_booking`, `update_booking`, `cancel_booking`, `get_booking_status`, `dispatch_booking`, `get_available_vehicles`, `get_driver_details`, `get_fare_quote` | Supabase (`booking_db.py`) |
| `search_customer`, `create_customer`, `update_customer` | Supabase (`booking_db.py`) |
| `search_location` | Google Places API (New) (`places.py`) |
| `send_confirmation` | Telnyx Messaging API |
| `transfer_to_human` | Logs + speaks a handoff line — wire in the real Telnyx Call Control "transfer" call once you have your dispatcher's SIP endpoint |
| `end_call` | Ends the Pipecat worker |

## 8. Latency benchmarking (vs. Retell)

`PipelineParams(enable_metrics=True, ...)` in `bot.py` makes Pipecat emit per-service timing
(STT/LLM/TTS ms) each turn. If you want these logged, add a small table in Supabase (e.g.
`call_metrics`) and write to it the same way `booking_db.py` writes everything else.

## What's NOT in this scaffold (by design)

- The monitoring dashboard front-end
- Retell AI setup (separate track)
- A real fare-pricing engine — `get_fare_quote` uses a flat base+per-km placeholder rate
  table in `booking_db.py`; swap in your actual pricing logic or an iCabbi pricing call.
- `transfer_to_human`'s actual SIP transfer call — currently just acknowledges and speaks a
  handoff line; wire the real Telnyx Call Control "transfer" API call in once you have your
  dispatcher's SIP endpoint.
