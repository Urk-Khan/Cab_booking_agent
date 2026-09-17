# Ashad — Dispatch Console

A Next.js dashboard for the [Ashad voice booking agent](../ashad-voice-agent). It reads
directly from the same Supabase project the voice agent writes to, and gives a
dispatcher a live view of calls, bookings, drivers, and the fleet.

## What's on it

| Page | Shows |
|---|---|
| **Overview** | Today's call/booking KPIs, call → booking conversion rate, active bookings, recent call feed |
| **Bookings** | Every booking — passenger, route, pickup time, assigned driver/vehicle, fare, status |
| **Call log** | Every inbound call, its transcript summary, outcome, and the booking it produced (if any) |
| **Drivers** | Roster with status, rating, and current vehicle assignment |
| **Fleet** | Every vehicle, its status, capacity, and assigned driver |
| **Customers** | Customer records with trip count and last-trip date |

It's read-only by design — it's a monitoring console, not a replacement for the
booking tools the LLM calls during a live conversation.

## Running it

```bash
npm install
cp .env.example .env.local
# fill in SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY — same values as the
# voice agent's own .env
npm run dev
```

Open `http://localhost:3000`.

If you skip the `.env.local` step, the dashboard still runs — it falls back to
built-in demo data (`lib/mock-data.ts`) so you can preview the UI without a live
database. A "Demo data" badge appears in the top bar whenever this fallback is
active.

## How it connects to the existing schema

`lib/types.ts` mirrors the tables created by `icabbi_taxi_schema.sql`
(`bookings`, `customers`, `vehicles`, `drivers`, `call_logs`, `fare_quotes`) —
no schema changes are needed. `lib/supabase.ts` uses the same service-role-key
pattern as the voice agent's own `supabase_client.py`, so it bypasses Row Level
Security the same way. That key is read from the server only
(`SUPABASE_SERVICE_ROLE_KEY`, no `NEXT_PUBLIC_` prefix) and every data-reading
page is a React Server Component, so it's never sent to the browser.

## Structure

```
app/
  layout.tsx          Root shell — sidebar + top bar
  page.tsx             Overview
  bookings/page.tsx
  calls/page.tsx
  drivers/page.tsx
  vehicles/page.tsx
  customers/page.tsx
components/            Sidebar, status badges, stat cards, panels
lib/
  supabase.ts          Server-side Supabase client
  data.ts              Data-access functions (live query + demo fallback)
  mock-data.ts          Demo fixtures
  types.ts             Types matching icabbi_taxi_schema.sql
  format.ts            Date/currency/phone formatting helpers
```

## Extending it

- **Realtime**: Supabase supports realtime subscriptions — the overview and
  call-log pages are natural candidates for wiring up `supabase.channel(...)`
  so new calls/bookings appear without a refresh.
- **`transfer_to_human` / dispatch actions**: the console is currently
  read-only. Adding write actions (e.g., manually reassigning a driver) means
  adding Route Handlers under `app/api/` that use the same service-role
  client, plus care around auth — this dashboard has none yet.
- **Auth**: there's no login wall here. Before deploying this anywhere
  reachable outside your own machine, put it behind Supabase Auth or your own
  SSO, since it displays customer PII (names, phone numbers, addresses).
