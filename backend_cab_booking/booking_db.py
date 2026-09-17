"""
Supabase-backed booking / customer / vehicle / driver / fare-quote operations.

Mirrors icabbi_taxi_schema.sql 1:1 — see that file for the table and view definitions this
module reads and writes (customers, vehicles, drivers, bookings, dispatch_history,
fare_quotes, plus the booking_details / customer_booking_history views). booking_ref
generation and booking_status_history logging both happen automatically via triggers in
that schema — this module never writes to booking_status_history directly.

This is a pure data layer: no Pipecat, no FunctionCallParams, no result_callback. That seam
lives in tools.py, same pattern as places.py (Google Places) — keeping this layer separate
means it's testable without the voice pipeline and swappable if the backend ever changes.

supabase-py's client is synchronous, so every query here is wrapped in asyncio.to_thread()
to avoid blocking the pipeline's event loop.
"""

import asyncio
import math

from loguru import logger

from supabase_client import get_supabase

# Simple flat-rate fare model: base fare + per-km rate, by vehicle_type. This is a
# placeholder estimate, not a real pricing engine — swap in your actual rate card or an
# iCabbi pricing call whenever you have one.
_FARE_RATES = {
    "standard": {"base": 4.00, "per_km": 1.75},
    "suv": {"base": 6.00, "per_km": 2.25},
    "van": {"base": 8.00, "per_km": 2.75},
    "premium": {"base": 10.00, "per_km": 3.25},
}
_DEFAULT_FARE_RATE = _FARE_RATES["standard"]

# Used as a fallback distance when we don't have coordinates for a fare quote, so the call
# isn't stuck without an answer. A rough placeholder, not a real estimate.
_FALLBACK_DISTANCE_KM = 5.0


def _haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two lat/lng points, in kilometers."""
    earth_radius_km = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return 2 * earth_radius_km * math.asin(math.sqrt(a))


async def _run(query_fn):
    """Run a blocking supabase-py call off the event loop.

    query_fn takes the Supabase client and returns an already-`.execute()`d response.
    Returns None if Supabase isn't configured, or if the query itself raises (e.g. a
    constraint violation) — callers treat None as "this operation didn't happen."
    """
    client = get_supabase()
    if client is None:
        return None
    try:
        return await asyncio.to_thread(query_fn, client)
    except Exception as e:
        logger.error(f"Supabase query failed: {e}")
        return None


# ---------------------------------------------------------------------------
# Customers
# ---------------------------------------------------------------------------


async def get_or_create_customer(name: str, phone: str) -> dict | None:
    """Find a customer by phone, or create one if they don't exist yet. Used internally by
    create_booking so every booking is linked to a customer record automatically."""
    existing = await _run(
        lambda c: c.table("customers").select("*").eq("phone", phone).maybe_single().execute()
    )
    if existing and existing.data:
        return existing.data

    created = await _run(
        lambda c: c.table("customers").insert({"name": name, "phone": phone}).execute()
    )
    return created.data[0] if created and created.data else None


async def search_customer(phone: str | None = None, customer_id: str | None = None) -> dict | None:
    if not phone and not customer_id:
        return None

    def query(c):
        table = c.table("customers").select("*")
        if customer_id:
            return table.eq("id", customer_id).maybe_single().execute()
        return table.eq("phone", phone).maybe_single().execute()

    result = await _run(query)
    return result.data if result else None


async def create_customer(
    name: str,
    phone: str,
    email: str | None = None,
    address: str | None = None,
    notes: str = "",
) -> dict | None:
    payload = {"name": name, "phone": phone, "email": email, "address": address, "notes": notes}
    result = await _run(lambda c: c.table("customers").insert(payload).execute())
    return result.data[0] if result and result.data else None


async def update_customer(customer_id: str, **fields) -> dict | None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return None
    result = await _run(
        lambda c: c.table("customers").update(fields).eq("id", customer_id).execute()
    )
    return result.data[0] if result and result.data else None


# ---------------------------------------------------------------------------
# Bookings
# ---------------------------------------------------------------------------


async def create_booking(
    passenger_name: str,
    passenger_phone: str,
    pickup_address: str,
    dropoff_address: str,
    pickup_datetime: str,
    passengers: int = 1,
    vehicle_type: str = "standard",
    notes: str = "",
    pickup_lat: float | None = None,
    pickup_lng: float | None = None,
    dropoff_lat: float | None = None,
    dropoff_lng: float | None = None,
    call_id: str | None = None,
) -> dict | None:
    """Create a booking. Also finds-or-creates the customer by phone so the booking is
    linked. booking_ref is generated automatically by a DB trigger."""
    customer = await get_or_create_customer(passenger_name, passenger_phone)

    payload = {
        "customer_id": customer["id"] if customer else None,
        "passenger_name": passenger_name,
        "passenger_phone": passenger_phone,
        "pickup_address": pickup_address,
        "pickup_lat": pickup_lat,
        "pickup_lng": pickup_lng,
        "dropoff_address": dropoff_address,
        "dropoff_lat": dropoff_lat,
        "dropoff_lng": dropoff_lng,
        "pickup_datetime": pickup_datetime,
        "passengers": passengers,
        "vehicle_type": vehicle_type,
        "notes": notes,
        "call_id": call_id,
    }
    result = await _run(lambda c: c.table("bookings").insert(payload).execute())
    return result.data[0] if result and result.data else None


async def view_booking(booking_ref: str) -> dict | None:
    """Full booking detail (customer + driver + vehicle joined in) via the booking_details
    view."""
    result = await _run(
        lambda c: c.table("booking_details")
        .select("*")
        .eq("booking_ref", booking_ref)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


async def update_booking(booking_ref: str, **fields) -> dict | None:
    fields = {k: v for k, v in fields.items() if v is not None}
    if not fields:
        return None
    result = await _run(
        lambda c: c.table("bookings").update(fields).eq("booking_ref", booking_ref).execute()
    )
    return result.data[0] if result and result.data else None


async def cancel_booking(booking_ref: str, cancellation_reason: str = "") -> dict | None:
    result = await _run(
        lambda c: c.table("bookings")
        .update({"status": "cancelled", "cancellation_reason": cancellation_reason})
        .eq("booking_ref", booking_ref)
        .execute()
    )
    return result.data[0] if result and result.data else None


async def get_booking_status(booking_ref: str) -> dict | None:
    result = await _run(
        lambda c: c.table("bookings")
        .select("booking_ref, status, pickup_datetime")
        .eq("booking_ref", booking_ref)
        .maybe_single()
        .execute()
    )
    return result.data if result else None


async def get_driver_details(booking_ref: str) -> dict | None:
    result = await _run(
        lambda c: c.table("booking_details")
        .select("driver_name, driver_phone, plate_number, assigned_vehicle_type")
        .eq("booking_ref", booking_ref)
        .maybe_single()
        .execute()
    )
    if not result or not result.data or not result.data.get("driver_name"):
        return None
    return result.data


# ---------------------------------------------------------------------------
# Vehicles / dispatch
# ---------------------------------------------------------------------------


async def get_available_vehicles(vehicle_type: str | None = None, limit: int = 5) -> list[dict]:
    def query(c):
        q = c.table("vehicles").select("*").eq("status", "available")
        if vehicle_type:
            q = q.eq("vehicle_type", vehicle_type)
        return q.limit(limit).execute()

    result = await _run(query)
    return result.data if result and result.data else []


async def dispatch_booking(
    booking_ref: str, vehicle_id: str | None = None, driver_id: str | None = None
) -> dict | None:
    """Assign a vehicle/driver to a booking, set it to 'dispatched', and log the assignment
    in dispatch_history (kept separate from the booking's current driver/vehicle so
    reassignments have a full audit trail)."""
    booking = await _run(
        lambda c: c.table("bookings")
        .select("id")
        .eq("booking_ref", booking_ref)
        .maybe_single()
        .execute()
    )
    if not booking or not booking.data:
        return None
    booking_id = booking.data["id"]

    updated = await _run(
        lambda c: c.table("bookings")
        .update({"status": "dispatched", "vehicle_id": vehicle_id, "driver_id": driver_id})
        .eq("id", booking_id)
        .execute()
    )

    await _run(
        lambda c: c.table("dispatch_history")
        .insert({"booking_id": booking_id, "vehicle_id": vehicle_id, "driver_id": driver_id})
        .execute()
    )

    return updated.data[0] if updated and updated.data else None


# ---------------------------------------------------------------------------
# Fare quotes
# ---------------------------------------------------------------------------


async def get_fare_quote(
    pickup_address: str,
    dropoff_address: str,
    pickup_datetime: str | None = None,
    passengers: int = 1,
    vehicle_type: str = "standard",
    pickup_lat: float | None = None,
    pickup_lng: float | None = None,
    dropoff_lat: float | None = None,
    dropoff_lng: float | None = None,
) -> dict:
    """Estimate a fare and log it to fare_quotes, whether or not it turns into a booking."""
    rate = _FARE_RATES.get(vehicle_type, _DEFAULT_FARE_RATE)

    if None not in (pickup_lat, pickup_lng, dropoff_lat, dropoff_lng):
        distance_km = _haversine_km(pickup_lat, pickup_lng, dropoff_lat, dropoff_lng)
    else:
        distance_km = _FALLBACK_DISTANCE_KM

    estimated_fare = round(rate["base"] + rate["per_km"] * distance_km, 2)

    quote = {
        "pickup_address": pickup_address,
        "dropoff_address": dropoff_address,
        "pickup_datetime": pickup_datetime,
        "passengers": passengers,
        "vehicle_type": vehicle_type,
        "estimated_fare": estimated_fare,
        "currency": "GBP",  # Ashad Cabs operates in the UK only (see prompts.py / places.py)
    }

    await _run(lambda c: c.table("fare_quotes").insert(quote).execute())

    return quote
