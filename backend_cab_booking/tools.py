"""
Function-calling tools exposed to the LLM (Pipecat 1.8.1 API).

Pipecat 1.8+ auto-generates each tool's schema from its name, type hints, and docstring —
there's no separate FunctionSchema/register_function step. Just list these functions on the
LLMContext: LLMContext(tools=CAB_BOOKING_TOOLS).

No N8N anywhere — every tool talks to its backend directly:

- Booking/customer/vehicle/driver/fare tools -> booking_db.py -> Supabase directly
  (see icabbi_taxi_schema.sql for the tables/views). booking_ref generation and booking
  status-history logging happen automatically via DB triggers.
- search_location -> places.py -> Google Places API (New) directly.
- send_confirmation -> Telnyx Messaging API directly (same account as the call itself).
- transfer_to_human speaks a handoff line; wire in the actual Telnyx Call Control "transfer"
  API once you have your dispatcher's SIP endpoint.

Keep handlers thin: validate/shape input, call the data layer, return a small structured
result the LLM can speak from. Business logic (fare rates, customer lookup-or-create,
dispatch bookkeeping) lives in booking_db.py, not here.
"""

import os

import aiohttp
from loguru import logger
from pipecat.frames.frames import EndWorkerFrame
from pipecat.services.llm_service import FunctionCallParams

import booking_db
from places import search_location as _search_location

TELNYX_API_KEY = os.getenv("TELNYX_API_KEY", "")
TELNYX_SMS_FROM_NUMBER = os.getenv("TELNYX_SMS_FROM_NUMBER", "")
_TELNYX_MESSAGES_URL = "https://api.telnyx.com/v2/messages"

_REQUEST_TIMEOUT = aiohttp.ClientTimeout(total=6)  # keep tool calls fast; caller is on hold


# =============================================================================
# BOOKINGS (Supabase — booking_db.py)
# =============================================================================


async def create_booking(
    params: FunctionCallParams,
    passenger_name: str,
    passenger_phone: str,
    pickup_address: str,
    dropoff_address: str,
    pickup_datetime: str,
    passengers: int = 1,
    vehicle_type: str = "standard",
    notes: str = "",
):
    """Create a booking after the caller has confirmed the required details.
Args:
    passenger_name: Caller name.
    passenger_phone: Caller phone.
    pickup_address: Precise resolved pickup address.
    dropoff_address: Precise resolved destination address.
    pickup_datetime: Pickup time as ISO 8601 datetime.
    passengers: Passenger count.
    vehicle_type: standard, suv, van, or premium.
    notes: Optional special instructions.
    """
    app_resources = params.app_resources or {}
    booking = await booking_db.create_booking(
        passenger_name=passenger_name,
        passenger_phone=passenger_phone or app_resources.get("caller_phone"),
        pickup_address=pickup_address,
        dropoff_address=dropoff_address,
        pickup_datetime=pickup_datetime,
        passengers=passengers,
        vehicle_type=vehicle_type,
        notes=notes,
        call_id=app_resources.get("session_id"),
    )
    if not booking:
        await params.result_callback({"success": False, "error": "booking_failed"})
        return
    await params.result_callback(
        {
            "success": True,
            "booking_ref": booking.get("booking_ref"),
            "status": booking.get("status", "pending"),
        }
    )


async def view_booking(params: FunctionCallParams, booking_id: str):
    """Get full booking details by booking reference.
Args:
    booking_id: Booking reference.
    """
    booking = await booking_db.view_booking(booking_id)
    if not booking:
        await params.result_callback({"success": False, "error": "not_found"})
        return
    await params.result_callback({"success": True, "booking": booking})


async def update_booking(
    params: FunctionCallParams,
    booking_id: str,
    pickup_address: str = None,
    dropoff_address: str = None,
    pickup_datetime: str = None,
    passenger_name: str = None,
    passenger_phone: str = None,
    passengers: int = None,
    vehicle_type: str = None,
    notes: str = None,
):
    """Update only the booking fields that are changing.
Args:
    booking_id: Booking reference.
    pickup_address: New precise resolved pickup, if changing.
    dropoff_address: New precise resolved destination, if changing.
    pickup_datetime: New pickup time as ISO 8601, if changing.
    passenger_name: New name, if changing.
    passenger_phone: New phone, if changing.
    passengers: New passenger count, if changing.
    vehicle_type: New vehicle type, if changing.
    notes: New notes, if changing.
    """
    booking = await booking_db.update_booking(
        booking_id,
        pickup_address=pickup_address,
        dropoff_address=dropoff_address,
        pickup_datetime=pickup_datetime,
        passenger_name=passenger_name,
        passenger_phone=passenger_phone,
        passengers=passengers,
        vehicle_type=vehicle_type,
        notes=notes,
    )
    if not booking:
        await params.result_callback({"success": False, "error": "update_failed"})
        return
    await params.result_callback({"success": True, "booking": booking})


async def cancel_booking(params: FunctionCallParams, booking_id: str, cancellation_reason: str = ""):
    """Cancel an existing booking.
Args:
    booking_id: Booking reference.
    cancellation_reason: Reason, if given.
    """
    booking = await booking_db.cancel_booking(booking_id, cancellation_reason)
    if not booking:
        await params.result_callback({"success": False, "error": "cancel_failed"})
        return
    await params.result_callback({"success": True, "status": booking.get("status")})


async def get_booking_status(params: FunctionCallParams, booking_id: str):
    """Get the current booking status.
Args:
    booking_id: Booking reference.
    """
    status = await booking_db.get_booking_status(booking_id)
    if not status:
        await params.result_callback({"success": False, "error": "not_found"})
        return
    await params.result_callback({"success": True, **status})


async def get_driver_details(params: FunctionCallParams, booking_id: str):
    """Get the assigned driver and vehicle for a booking.
Args:
    booking_id: Booking reference.
    """
    details = await booking_db.get_driver_details(booking_id)
    if not details:
        await params.result_callback({"success": False, "error": "no_driver_assigned"})
        return
    await params.result_callback({"success": True, **details})


async def get_fare_quote(
    params: FunctionCallParams,
    pickup_address: str,
    dropoff_address: str,
    pickup_datetime: str = None,
    passengers: int = 1,
    vehicle_type: str = "standard",
):
    """Get an estimated fare.
Args:
    pickup_address: Resolved pickup address.
    dropoff_address: Resolved destination address.
    pickup_datetime: ISO 8601 time, if known.
    passengers: Passenger count.
    vehicle_type: standard, suv, van, or premium.
    """
    quote = await booking_db.get_fare_quote(
        pickup_address=pickup_address,
        dropoff_address=dropoff_address,
        pickup_datetime=pickup_datetime,
        passengers=passengers,
        vehicle_type=vehicle_type,
    )
    await params.result_callback({"success": True, **quote})


async def dispatch_booking(
    params: FunctionCallParams, booking_id: str, vehicle_id: str = None, driver_id: str = None
):
    """Manually assign or reassign a vehicle/driver when the caller explicitly requests it.
Args:
    booking_id: Booking reference.
    vehicle_id: Vehicle id, if specified.
    driver_id: Driver id, if specified.
    """
    booking = await booking_db.dispatch_booking(booking_id, vehicle_id, driver_id)
    if not booking:
        await params.result_callback({"success": False, "error": "dispatch_failed"})
        return
    await params.result_callback({"success": True, "status": booking.get("status")})


async def get_available_vehicles(params: FunctionCallParams, vehicle_type: str = None):
    """Check available vehicle types.
Args:
    vehicle_type: Optional filter: standard, suv, van, or premium.
    """
    vehicles = await booking_db.get_available_vehicles(vehicle_type)
    await params.result_callback({"success": True, "available": vehicles})


# =============================================================================
# CUSTOMERS (Supabase — booking_db.py)
# =============================================================================


async def search_customer(params: FunctionCallParams, phone: str = None, customer_id: str = None):
    """Find an existing customer by phone or customer id.
Args:
    phone: Caller phone, if known.
    customer_id: Customer id, if known.
    """
    customer = await booking_db.search_customer(phone, customer_id)
    if not customer:
        await params.result_callback({"success": False, "error": "not_found"})
        return
    await params.result_callback({"success": True, "customer": customer})


async def create_customer(
    params: FunctionCallParams,
    name: str,
    phone: str,
    email: str = None,
    address: str = None,
    notes: str = "",
):
    """Create a customer profile when explicitly requested without a booking.
Args:
    name: Customer name.
    phone: Customer phone.
    email: Optional email.
    address: Optional address.
    notes: Optional notes.
    """
    customer = await booking_db.create_customer(name, phone, email, address, notes)
    if not customer:
        await params.result_callback({"success": False, "error": "create_failed"})
        return
    await params.result_callback({"success": True, "customer": customer})


async def update_customer(
    params: FunctionCallParams,
    customer_id: str,
    name: str = None,
    phone: str = None,
    email: str = None,
    address: str = None,
    notes: str = None,
):
    """Update saved customer details.
Args:
    customer_id: Customer id.
    name: New name, if changing.
    phone: New phone, if changing.
    email: New email, if changing.
    address: New address, if changing.
    notes: New notes, if changing.
    """
    customer = await booking_db.update_customer(
        customer_id, name=name, phone=phone, email=email, address=address, notes=notes
    )
    if not customer:
        await params.result_callback({"success": False, "error": "update_failed"})
        return
    await params.result_callback({"success": True, "customer": customer})


# =============================================================================
# LOCATION (Google Places — places.py)
# =============================================================================


async def search_location(params: FunctionCallParams, query: str):
    """Resolve a pickup/drop-off into a precise current UK place.
Use for landmarks, businesses, partial addresses, intersections, cities/towns, or addresses missing a city.
The result includes:
- in_service_area: false means outside the UK.
- precise: false means more location detail is needed.
Args:
    query: Caller location plus known city/town context.
    """
    matches = await _search_location(query)

    if not matches:
        await params.result_callback({"success": False, "in_service_area": None, "matches": []})
        return

    uk_matches = [m for m in matches if m["in_uk"]]

    if not uk_matches:
        # Every candidate is outside the UK — nothing to offer the caller.
        await params.result_callback({"success": True, "in_service_area": False, "matches": []})
        return

    precise_matches = [m for m in uk_matches if m["precise"]]
    best_matches = precise_matches or uk_matches

    await params.result_callback(
        {
            "success": True,
            "in_service_area": True,
            "precise": bool(precise_matches),
            "matches": [
                {
                    "name": m["name"],
                    "address": m["formatted_address"],
                    "place_id": m["place_id"],
                    "latitude": m["latitude"],
                    "longitude": m["longitude"],
                }
                for m in best_matches
            ],
        }
    )


# =============================================================================
# SMS / CALL CONTROL (Telnyx, direct)
# =============================================================================


async def send_confirmation(params: FunctionCallParams, phone_number: str, booking_ref: str):
    """Send a booking confirmation SMS.
Args:
    phone_number: Customer phone in E.164 format.
    booking_ref: Booking reference.
    """
    if not TELNYX_API_KEY or not TELNYX_SMS_FROM_NUMBER:
        logger.error("TELNYX_API_KEY / TELNYX_SMS_FROM_NUMBER not set in .env — cannot send SMS.")
        await params.result_callback({"success": False, "error": "sms_service_unavailable"})
        return

    payload = {
        "from": TELNYX_SMS_FROM_NUMBER,
        "to": phone_number,
        "text": f"Your ride is booked! Reference: {booking_ref}. Thanks for riding with us.",
    }
    headers = {"Authorization": f"Bearer {TELNYX_API_KEY}", "Content-Type": "application/json"}

    try:
        async with aiohttp.ClientSession(timeout=_REQUEST_TIMEOUT) as session:
            async with session.post(_TELNYX_MESSAGES_URL, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                await resp.json(content_type=None)
        await params.result_callback({"success": True, "sent": True})
    except Exception as e:
        logger.error(f"send_confirmation (Telnyx SMS) failed: {e}")
        await params.result_callback({"success": False, "error": "sms_service_unavailable"})


async def transfer_to_human(params: FunctionCallParams, reason: str):
    """Transfer the live call to a human dispatcher.
Args:
    reason: Short reason for the transfer.
    """
    # Speaks a handoff line; the actual SIP transfer needs your dispatcher's SIP endpoint
    # wired in here via the Telnyx Call Control "transfer" API once you have it.
    logger.info(f"Transfer requested: {reason}")
    await params.result_callback({"success": True, "transferring": True})


async def end_call(params: FunctionCallParams):
    """End the call after the caller is finished.
No arguments.
    """
    await params.result_callback({"success": True})
    # Downstream so queued speech (the bot's goodbye) finishes before the pipeline ends.
    await params.llm.push_frame(EndWorkerFrame())


CAB_BOOKING_TOOLS = [
    create_booking,
    view_booking,
    update_booking,
    cancel_booking,
    get_booking_status,
    get_driver_details,
    get_fare_quote,
    dispatch_booking,
    get_available_vehicles,
    search_customer,
    create_customer,
    update_customer,
    search_location,
    send_confirmation,
    transfer_to_human,
    end_call,
]