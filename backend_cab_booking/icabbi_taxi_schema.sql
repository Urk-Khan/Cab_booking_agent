-- ============================================================
-- iCabbi Taxi AI Agent — Supabase Schema
-- ============================================================
-- Covers: create_booking, view_booking, update_booking, cancel_booking,
-- get_booking_status, get_fare_quote, get_driver_details, search_customer,
-- create_customer, update_customer, get_available_vehicles, dispatch_booking
--
-- Run this in the Supabase SQL Editor (or via `supabase db push` / migrations).
-- Safe to re-run: every statement is IF NOT EXISTS / OR REPLACE.
-- ============================================================

create extension if not exists pgcrypto;   -- gen_random_uuid()

-- ------------------------------------------------------------
-- ENUM TYPES
-- ------------------------------------------------------------

do $$ begin
    create type booking_status as enum (
        'pending',      -- created, not yet dispatched
        'confirmed',    -- confirmed with customer
        'dispatched',   -- vehicle/driver assigned
        'en_route',     -- driver heading to pickup
        'in_progress',  -- passenger picked up, trip underway
        'completed',
        'cancelled',
        'no_show'
    );
exception when duplicate_object then null; end $$;

do $$ begin
    create type vehicle_status as enum ('available', 'busy', 'offline', 'maintenance');
exception when duplicate_object then null; end $$;

do $$ begin
    create type driver_status as enum ('available', 'busy', 'offline', 'on_break');
exception when duplicate_object then null; end $$;

-- ------------------------------------------------------------
-- updated_at auto-touch trigger (shared by every table below)
-- ------------------------------------------------------------

create or replace function set_updated_at()
returns trigger as $$
begin
    new.updated_at = now();
    return new;
end;
$$ language plpgsql;

-- ============================================================
-- CUSTOMERS
-- ============================================================

create table if not exists customers (
    id          uuid primary key default gen_random_uuid(),
    name        text not null,
    phone       text not null unique,        -- E.164, e.g. +14155551234
    email       text,
    address     text,                        -- default/home address, optional
    notes       text default '',
    created_at  timestamptz not null default now(),
    updated_at  timestamptz not null default now()
);

create index if not exists idx_customers_phone on customers (phone);
create index if not exists idx_customers_name   on customers using gin (to_tsvector('simple', name));

drop trigger if exists trg_customers_updated_at on customers;
create trigger trg_customers_updated_at
    before update on customers
    for each row execute function set_updated_at();

-- ============================================================
-- VEHICLES
-- ============================================================

create table if not exists vehicles (
    id            uuid primary key default gen_random_uuid(),
    plate_number  text not null unique,
    vehicle_type  text not null default 'standard',   -- standard / suv / van / premium / wheelchair ...
    capacity      int  not null default 4 check (capacity > 0),
    status        vehicle_status not null default 'available',
    created_at    timestamptz not null default now(),
    updated_at    timestamptz not null default now()
);

create index if not exists idx_vehicles_status on vehicles (status);
create index if not exists idx_vehicles_type   on vehicles (vehicle_type);

drop trigger if exists trg_vehicles_updated_at on vehicles;
create trigger trg_vehicles_updated_at
    before update on vehicles
    for each row execute function set_updated_at();

-- ============================================================
-- DRIVERS
-- ============================================================

create table if not exists drivers (
    id              uuid primary key default gen_random_uuid(),
    name            text not null,
    phone           text not null unique,
    license_number  text unique,
    status          driver_status not null default 'offline',
    rating          numeric(2,1) check (rating between 0 and 5),
    vehicle_id      uuid references vehicles(id) on delete set null,  -- currently-assigned vehicle
    created_at      timestamptz not null default now(),
    updated_at      timestamptz not null default now()
);

create index if not exists idx_drivers_status     on drivers (status);
create index if not exists idx_drivers_vehicle_id on drivers (vehicle_id);

drop trigger if exists trg_drivers_updated_at on drivers;
create trigger trg_drivers_updated_at
    before update on drivers
    for each row execute function set_updated_at();

-- ============================================================
-- BOOKINGS
-- ============================================================

create table if not exists bookings (
    id                 uuid primary key default gen_random_uuid(),
    booking_ref        text not null unique,   -- short human-readable code, e.g. CAB-A1B2C3

    customer_id        uuid references customers(id) on delete set null,
    passenger_name     text not null,
    passenger_phone    text not null,

    pickup_address     text not null,
    pickup_lat         double precision,
    pickup_lng         double precision,
    dropoff_address    text not null,
    dropoff_lat        double precision,
    dropoff_lng        double precision,

    pickup_datetime    timestamptz not null,
    passengers         int not null default 1 check (passengers > 0),
    vehicle_type       text not null default 'standard',
    notes              text default '',

    status             booking_status not null default 'pending',
    vehicle_id         uuid references vehicles(id) on delete set null,
    driver_id          uuid references drivers(id) on delete set null,

    fare_amount        numeric(10,2),
    fare_currency      text default 'GBP',  -- Ashad Cabs operates in the UK only

    cancellation_reason text,

    source             text default 'ai_voice_agent',   -- where the booking came from
    call_id            text,                             -- ties back to the voice session

    created_at         timestamptz not null default now(),
    updated_at         timestamptz not null default now()
);

create index if not exists idx_bookings_status          on bookings (status);
create index if not exists idx_bookings_customer_id      on bookings (customer_id);
create index if not exists idx_bookings_pickup_datetime   on bookings (pickup_datetime);
create index if not exists idx_bookings_booking_ref       on bookings (booking_ref);
create index if not exists idx_bookings_call_id           on bookings (call_id);

drop trigger if exists trg_bookings_updated_at on bookings;
create trigger trg_bookings_updated_at
    before update on bookings
    for each row execute function set_updated_at();

-- Auto-generate a short booking_ref like CAB-7F3A2B if one wasn't supplied.
create or replace function generate_booking_ref()
returns trigger as $$
begin
    if new.booking_ref is null or new.booking_ref = '' then
        new.booking_ref := 'CAB-' || upper(substr(replace(gen_random_uuid()::text, '-', ''), 1, 6));
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_bookings_generate_ref on bookings;
create trigger trg_bookings_generate_ref
    before insert on bookings
    for each row execute function generate_booking_ref();

-- ============================================================
-- HISTORY / AUDIT TABLES
-- ============================================================

-- 1) Every status change a booking goes through (pending -> confirmed -> dispatched -> ...).
--    This is what answers "what happened to booking X and when".
create table if not exists booking_status_history (
    id          uuid primary key default gen_random_uuid(),
    booking_id  uuid not null references bookings(id) on delete cascade,
    old_status  booking_status,
    new_status  booking_status not null,
    changed_by  text default 'ai_voice_agent',   -- 'ai_voice_agent' / 'dispatcher' / 'system'
    note        text,
    created_at  timestamptz not null default now()
);

create index if not exists idx_bsh_booking_id on booking_status_history (booking_id);
create index if not exists idx_bsh_created_at on booking_status_history (created_at);

-- Auto-log every status change on bookings into booking_status_history.
create or replace function log_booking_status_change()
returns trigger as $$
begin
    if (tg_op = 'INSERT') or (old.status is distinct from new.status) then
        insert into booking_status_history (booking_id, old_status, new_status)
        values (new.id, case when tg_op = 'INSERT' then null else old.status end, new.status);
    end if;
    return new;
end;
$$ language plpgsql;

drop trigger if exists trg_bookings_log_status on bookings;
create trigger trg_bookings_log_status
    after insert or update on bookings
    for each row execute function log_booking_status_change();

-- 2) Every call the voice agent handled — which customer called, what it was about, and
--    which booking (if any) it resulted in. This is the "which customer, what booking" log.
create table if not exists call_logs (
    id               uuid primary key default gen_random_uuid(),
    call_id          text unique,                 -- session id from the voice pipeline
    customer_id      uuid references customers(id) on delete set null,
    customer_phone   text,
    booking_id       uuid references bookings(id) on delete set null,
    call_outcome     text,                         -- 'booking_created' / 'booking_updated' /
                                                     -- 'cancelled' / 'transferred' / 'no_action' / ...
    transcript_summary text,
    started_at       timestamptz not null default now(),
    ended_at         timestamptz,
    duration_seconds int
);

create index if not exists idx_call_logs_customer_id on call_logs (customer_id);
create index if not exists idx_call_logs_booking_id   on call_logs (booking_id);
create index if not exists idx_call_logs_call_id      on call_logs (call_id);

-- 3) Fare quotes given out — including ones that never turned into a booking.
create table if not exists fare_quotes (
    id                uuid primary key default gen_random_uuid(),
    customer_id       uuid references customers(id) on delete set null,
    booking_id        uuid references bookings(id) on delete set null,  -- filled in if it converted
    pickup_address    text not null,
    dropoff_address   text not null,
    pickup_datetime   timestamptz,
    passengers        int default 1,
    vehicle_type      text default 'standard',
    estimated_fare    numeric(10,2),
    currency          text default 'GBP',  -- Ashad Cabs operates in the UK only
    created_at        timestamptz not null default now()
);

create index if not exists idx_fare_quotes_customer_id on fare_quotes (customer_id);
create index if not exists idx_fare_quotes_booking_id  on fare_quotes (booking_id);

-- 4) Dispatch assignment history — every vehicle/driver assignment attempt for a booking,
--    including reassignments (a booking's *current* driver/vehicle still lives on bookings
--    itself; this table is the full history of assignments, not just the latest one).
create table if not exists dispatch_history (
    id            uuid primary key default gen_random_uuid(),
    booking_id    uuid not null references bookings(id) on delete cascade,
    vehicle_id    uuid references vehicles(id) on delete set null,
    driver_id     uuid references drivers(id) on delete set null,
    dispatched_at timestamptz not null default now(),
    status        text default 'assigned'   -- 'assigned' / 'reassigned' / 'unassigned'
);

create index if not exists idx_dispatch_history_booking_id on dispatch_history (booking_id);

-- ============================================================
-- CONVENIENCE VIEWS
-- ============================================================

-- Full booking detail in one row — what view_booking / get_booking_status would select from.
create or replace view booking_details as
select
    b.id,
    b.booking_ref,
    b.status,
    b.pickup_address,
    b.dropoff_address,
    b.pickup_datetime,
    b.passengers,
    b.vehicle_type,
    b.fare_amount,
    b.fare_currency,
    c.name  as customer_name,
    c.phone as customer_phone,
    d.name  as driver_name,
    d.phone as driver_phone,
    v.plate_number,
    v.vehicle_type as assigned_vehicle_type,
    b.created_at,
    b.updated_at
from bookings b
left join customers c on c.id = b.customer_id
left join drivers   d on d.id = b.driver_id
left join vehicles  v on v.id = b.vehicle_id;

-- A customer's full ride history — what search_customer's "show me their bookings" needs.
create or replace view customer_booking_history as
select
    c.id   as customer_id,
    c.name as customer_name,
    c.phone as customer_phone,
    b.id as booking_id,
    b.booking_ref,
    b.status,
    b.pickup_address,
    b.dropoff_address,
    b.pickup_datetime,
    b.fare_amount,
    b.created_at
from customers c
join bookings b on b.customer_id = c.id
order by b.pickup_datetime desc;

-- ============================================================
-- ROW LEVEL SECURITY
-- ============================================================
-- RLS is enabled by default on new Supabase projects' public schema tables.
-- Your voice-agent backend should use the Supabase *service role* key (server-side only,
-- never exposed to a client), which bypasses RLS automatically — so no policies are
-- strictly required for that path. Still, it's good practice to enable RLS explicitly and
-- add policies once you expose any of this to client-side/anon access (e.g. a dispatcher
-- dashboard). Minimal example if/when you need it:
--
-- alter table bookings enable row level security;
-- create policy "service role full access" on bookings
--   for all using (auth.role() = 'service_role');
