# Cab Booking Agent — Voice Bot & Dispatch System

An end-to-end, production-ready AI cab booking platform featuring an inbound conversational voice agent and a real-time web dispatch dashboard.

Callers can book rides over the phone via natural speech. The voice agent validates UK addresses via the Google Places API, quotes fares, writes bookings to Supabase, and dispatches SMS confirmations via Telnyx — while operators monitor and manage rides live in the Next.js dispatch console.

---

## System Architecture

```text
                                       +----------------------------+
                                       |      Caller on Phone       |
                                       +--------------+-------------+
                                                      |
                                           Telnyx Telephony / SIP
                                                      |
                                                      v
                                       +----------------------------+
                                       |    backend_cab_booking     |
                                       | (Pipecat 1.8.1 Voice Bot)  |
                                       +--------------+-------------+
                                       | - Cartesia STT (Ink-Whisper|
                                       | - OpenAI / Anthropic LLM   |
                                       | - Cartesia TTS (Sonic)     |
                                       | - Google Places API (New)  |
                                       | - Telnyx SMS Confirmation  |
                                       +--------------+-------------+
                                                      |
                                         SQL Read / Write (PostgREST)
                                                      |
                                                      v
                                       +----------------------------+
                                       |      Supabase Database     |
                                       |  (Bookings, Drivers, Fleet)|
                                       +--------------+-------------+
                                                      ^
                                                      |
                                            Real-time Supabase Sync
                                                      |
                                       +--------------+-------------+
                                       |    frontend_cab_booking    |
                                       | (Next.js Operator Console) |
                                       +----------------------------+
```

---

## Repository Structure

```text
Cab_booking_agent/
├── backend_cab_booking/     # Python voice bot & telephony service
│   ├── bot.py               # Pipecat cascade pipeline & WebSocket runner
│   ├── start_agent.py       # Auto-launcher: Cloudflare tunnel + Telnyx webhook + bot
│   ├── start_bot.bat        # Windows 1-click launcher
│   ├── tools.py             # LLM tool definitions (booking, pricing, places)
│   ├── booking_db.py        # Supabase database layer
│   ├── places.py            # Google Places API (New) UK location lookup
│   ├── prompts.py           # Conversational system prompts & business logic
│   ├── icabbi_taxi_schema.sql # Database schema for Supabase
│   ├── requirements.txt     # Python package dependencies
│   └── .env.example         # Backend environment variables template
│
├── frontend_cab_booking/    # Next.js dispatcher dashboard
│   ├── app/                 # Next.js App Router pages & API routes
│   ├── components/          # UI components & dispatch tables
│   ├── lib/                 # Supabase client & utilities
│   ├── package.json         # Node.js dependencies
│   └── .env.example         # Frontend environment variables template
│
├── .gitignore               # Root git ignore rules
└── README.md                # Project documentation
```

---

## Quickstart Guide

### 1. Database Setup (Supabase)

1. Create a project at [supabase.com](https://supabase.com).
2. Navigate to the **SQL Editor** in your Supabase project dashboard.
3. Open and run [`backend_cab_booking/icabbi_taxi_schema.sql`](backend_cab_booking/icabbi_taxi_schema.sql). This creates all tables:
   - `customers`, `drivers`, `vehicles`
   - `bookings`, `booking_status_history`
   - `call_logs`, `fare_quotes`, `dispatch_history`
4. Copy your **Project URL** and **Service Role Key** (from *Project Settings -> API*).

---

### 2. Backend Voice Agent Setup

#### Prerequisites
- Python 3.10 to 3.14
- API keys for **Telnyx**, **Cartesia**, **OpenAI** (or Anthropic), and **Google Places API**

#### Configuration
Navigate to `backend_cab_booking` and set up your `.env`:
```bash
cd backend_cab_booking
cp .env.example .env
```

Fill in your `.env` credentials:
- `TELNYX_API_KEY`, `TELNYX_ACCOUNT_SID`, `TELNYX_APP_ID`, `TELNYX_PHONE_NUMBER`
- `CARTESIA_API_KEY`, `CARTESIA_VOICE_ID`
- `OPENAI_API_KEY` (or `ANTHROPIC_API_KEY`)
- `GOOGLE_MAPS_API_KEY`
- `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`

#### Installation & Launch
```bash
# Install dependencies
pip install -r requirements.txt

# Start the agent with automatic Cloudflare tunnel & Telnyx sync
python start_agent.py
```
*(On Windows, you can also simply run `start_bot.bat`)*

When started, `start_agent.py` automatically:
1. Spawns a Cloudflare tunnel (`*.trycloudflare.com`).
2. Configures your Telnyx TeXML Application webhook URL to point to the live tunnel.
3. Launches the Pipecat runner on port `7860`.
4. Announces the active phone number ready to receive calls.

---

### 3. Frontend Dispatch Dashboard Setup

#### Prerequisites
- Node.js 18+ and npm

#### Configuration
Navigate to `frontend_cab_booking` and create your local environment file:
```bash
cd frontend_cab_booking
cp .env.example .env.local
```

Set your Supabase credentials:
```env
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
```

#### Installation & Launch
```bash
npm install
npm run dev
```

Open [http://localhost:3000](http://localhost:3000) in your browser to access the live dispatch console.

---

## Features

- **Voice Pipeline**: Low-latency voice processing using Cartesia STT (Ink-Whisper), streaming LLM responses, and Cartesia TTS (Sonic) over Telnyx WebSockets.
- **UK Address Validation**: Uses Google Places API (New) with precision detection (<500m bounding box) and UK country boundary verification.
- **Dynamic Fare Quoting**: Calculates real-time distance and estimated vehicle rates in GBP (£).
- **Automated Dispatch**: Creates booking records in Supabase and triggers SMS confirmations to passenger mobile numbers.
- **Dispatcher Operations**: Live booking tracking, status overrides, driver fleet allocation, and call log auditing.

---

## License

MIT License. See individual modules for details.
