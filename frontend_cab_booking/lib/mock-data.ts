import type { Booking, Customer, Vehicle, Driver, CallLog, FareQuote } from "./types";

// UK-themed demo data — Ashad Cabs only operates in the UK (see prompts.py), so this
// fallback data uses London addresses/landmarks, +44 numbers, GBP fares, and UK-style
// plates to match what a real deployment would actually look like.

const now = Date.now();
const min = 60_000;
const hr = 3_600_000;
const iso = (offsetMs: number) => new Date(now + offsetMs).toISOString();

export const mockVehicles: Vehicle[] = [
  { id: "v1", plate_number: "LB21 KXR", vehicle_type: "standard", capacity: 4, status: "busy", created_at: iso(-30 * 24 * hr), updated_at: iso(-4 * min) },
  { id: "v2", plate_number: "LB19 PQT", vehicle_type: "suv", capacity: 6, status: "available", created_at: iso(-40 * 24 * hr), updated_at: iso(-1 * hr) },
  { id: "v3", plate_number: "LB22 WVN", vehicle_type: "standard", capacity: 4, status: "busy", created_at: iso(-60 * 24 * hr), updated_at: iso(-12 * min) },
  { id: "v4", plate_number: "LB20 HDC", vehicle_type: "premium", capacity: 4, status: "offline", created_at: iso(-90 * 24 * hr), updated_at: iso(-6 * hr) },
  { id: "v5", plate_number: "LB18 ZMF", vehicle_type: "van", capacity: 8, status: "available", created_at: iso(-15 * 24 * hr), updated_at: iso(-25 * min) },
  { id: "v6", plate_number: "LB21 GJL", vehicle_type: "standard", capacity: 4, status: "maintenance", created_at: iso(-70 * 24 * hr), updated_at: iso(-2 * hr) },
];

export const mockDrivers: Driver[] = [
  { id: "d1", name: "Marcus Webb", phone: "+447911123456", license_number: "DL-88213", status: "busy", rating: 4.8, vehicle_id: "v1", created_at: iso(-200 * 24 * hr), updated_at: iso(-4 * min) },
  { id: "d2", name: "Priya Nair", phone: "+447911223344", license_number: "DL-77120", status: "available", rating: 4.9, vehicle_id: "v2", created_at: iso(-180 * 24 * hr), updated_at: iso(-1 * hr) },
  { id: "d3", name: "Omar Reyes", phone: "+447911334455", license_number: "DL-65031", status: "busy", rating: 4.6, vehicle_id: "v3", created_at: iso(-150 * 24 * hr), updated_at: iso(-12 * min) },
  { id: "d4", name: "Lena Faust", phone: "+447911445566", license_number: "DL-99871", status: "offline", rating: 4.7, vehicle_id: "v4", created_at: iso(-220 * 24 * hr), updated_at: iso(-6 * hr) },
  { id: "d5", name: "Tunde Adeyemi", phone: "+447911556677", license_number: "DL-40218", status: "available", rating: 5.0, vehicle_id: "v5", created_at: iso(-90 * 24 * hr), updated_at: iso(-25 * min) },
  { id: "d6", name: "Grace Kim", phone: "+447911667788", license_number: "DL-30442", status: "on_break", rating: 4.5, vehicle_id: null, created_at: iso(-110 * 24 * hr), updated_at: iso(-15 * min) },
];

export const mockCustomers: Customer[] = [
  { id: "c1", name: "Alicia Ferreira", phone: "+447700123456", email: "alicia.f@example.com", address: "24 Baker Street, London", notes: "", created_at: iso(-300 * 24 * hr), updated_at: iso(-4 * min) },
  { id: "c2", name: "Daniel Osei", phone: "+447700234567", email: null, address: "8 Canary Wharf, London", notes: "Prefers SUV", created_at: iso(-250 * 24 * hr), updated_at: iso(-40 * min) },
  { id: "c3", name: "Rachel Kim", phone: "+447700345678", email: "rkim@example.com", address: null, notes: "", created_at: iso(-100 * 24 * hr), updated_at: iso(-1 * hr) },
  { id: "c4", name: "Marcus Chen", phone: "+447700456789", email: null, address: "15 Shoreditch High Street, London", notes: "", created_at: iso(-60 * 24 * hr), updated_at: iso(-3 * hr) },
];

export const mockBookings: Booking[] = [
  { id: "b1", booking_ref: "CAB-7F3A2B", customer_id: "c1", passenger_name: "Alicia Ferreira", passenger_phone: "+447700123456", pickup_address: "24 Baker Street, London", dropoff_address: "Heathrow Airport, Terminal 5", pickup_datetime: iso(25 * min), passengers: 1, vehicle_type: "standard", notes: "", status: "en_route", vehicle_id: "v1", driver_id: "d1", fare_amount: 58.5, fare_currency: "GBP", cancellation_reason: null, source: "ai_voice_agent", call_id: "call_9931", created_at: iso(-18 * min), updated_at: iso(-4 * min) },
  { id: "b2", booking_ref: "CAB-A19DE0", customer_id: "c2", passenger_name: "Daniel Osei", passenger_phone: "+447700234567", pickup_address: "8 Canary Wharf, London", dropoff_address: "Gatwick Airport", pickup_datetime: iso(70 * min), passengers: 2, vehicle_type: "suv", notes: "2 large suitcases", status: "dispatched", vehicle_id: "v3", driver_id: "d3", fare_amount: 82.0, fare_currency: "GBP", cancellation_reason: null, source: "ai_voice_agent", call_id: "call_9928", created_at: iso(-50 * min), updated_at: iso(-12 * min) },
  { id: "b3", booking_ref: "CAB-5C8811", customer_id: "c3", passenger_name: "Rachel Kim", passenger_phone: "+447700345678", pickup_address: "Oxford Street, London", dropoff_address: "Hyde Park, London", pickup_datetime: iso(-20 * min), passengers: 1, vehicle_type: "standard", notes: "", status: "completed", vehicle_id: "v2", driver_id: "d2", fare_amount: 24.2, fare_currency: "GBP", cancellation_reason: null, source: "ai_voice_agent", call_id: "call_9902", created_at: iso(-70 * min), updated_at: iso(-15 * min) },
  { id: "b4", booking_ref: "CAB-2B77F4", customer_id: "c4", passenger_name: "Marcus Chen", passenger_phone: "+447700456789", pickup_address: "15 Shoreditch High Street, London", dropoff_address: "London City Airport", pickup_datetime: iso(-90 * min), passengers: 1, vehicle_type: "standard", notes: "", status: "cancelled", vehicle_id: null, driver_id: null, fare_amount: null, fare_currency: "GBP", cancellation_reason: "Customer found alternate ride", source: "ai_voice_agent", call_id: "call_9887", created_at: iso(-95 * min), updated_at: iso(-88 * min) },
  { id: "b5", booking_ref: "CAB-D40129", customer_id: "c1", passenger_name: "Alicia Ferreira", passenger_phone: "+447700123456", pickup_address: "Heathrow Airport, Terminal 5", dropoff_address: "24 Baker Street, London", pickup_datetime: iso(3 * hr), passengers: 1, vehicle_type: "standard", notes: "Return trip", status: "pending", vehicle_id: null, driver_id: null, fare_amount: null, fare_currency: "GBP", cancellation_reason: null, source: "ai_voice_agent", call_id: "call_9931", created_at: iso(-4 * min), updated_at: iso(-4 * min) },
  { id: "b6", booking_ref: "CAB-99AB21", customer_id: "c2", passenger_name: "Daniel Osei", passenger_phone: "+447700234567", pickup_address: "Piccadilly Circus, London", dropoff_address: "The O2 Arena, London", pickup_datetime: iso(-200 * min), passengers: 3, vehicle_type: "suv", notes: "", status: "completed", vehicle_id: "v2", driver_id: "d2", fare_amount: 31.75, fare_currency: "GBP", cancellation_reason: null, source: "ai_voice_agent", call_id: "call_9840", created_at: iso(-210 * min), updated_at: iso(-160 * min) },
  { id: "b7", booking_ref: "CAB-6E2C90", customer_id: "c3", passenger_name: "Rachel Kim", passenger_phone: "+447700345678", pickup_address: "King's Cross Station, London", dropoff_address: "Camden Market, London", pickup_datetime: iso(10 * min), passengers: 1, vehicle_type: "standard", notes: "", status: "confirmed", vehicle_id: null, driver_id: null, fare_amount: 16.0, fare_currency: "GBP", cancellation_reason: null, source: "ai_voice_agent", call_id: "call_9935", created_at: iso(-2 * min), updated_at: iso(-2 * min) },
];

export const mockCallLogs: CallLog[] = [
  { id: "cl1", call_id: "call_9935", customer_id: "c3", customer_phone: "+447700345678", booking_id: "b7", call_outcome: "booking_created", transcript_summary: "Booked a ride from King's Cross Station to Camden Market for one passenger.", started_at: iso(-3 * min), ended_at: iso(-2 * min), duration_seconds: 74 },
  { id: "cl2", call_id: "call_9931", customer_id: "c1", customer_phone: "+447700123456", booking_id: "b1", call_outcome: "booking_created", transcript_summary: "Booked airport ride to Heathrow, then called back and added a return trip.", started_at: iso(-19 * min), ended_at: iso(-16 * min), duration_seconds: 189 },
  { id: "cl3", call_id: "call_9928", customer_id: "c2", customer_phone: "+447700234567", booking_id: "b2", call_outcome: "booking_created", transcript_summary: "Booked SUV to Gatwick Airport, mentioned two large suitcases.", started_at: iso(-52 * min), ended_at: iso(-49 * min), duration_seconds: 165 },
  { id: "cl4", call_id: "call_9902", customer_id: "c3", customer_phone: "+447700345678", booking_id: "b3", call_outcome: "booking_created", transcript_summary: "Booked standard ride from Oxford Street to Hyde Park.", started_at: iso(-72 * min), ended_at: iso(-69 * min), duration_seconds: 142 },
  { id: "cl5", call_id: "call_9887", customer_id: "c4", customer_phone: "+447700456789", booking_id: "b4", call_outcome: "cancelled", transcript_summary: "Booked then called back two minutes later to cancel.", started_at: iso(-96 * min), ended_at: iso(-93 * min), duration_seconds: 58 },
  { id: "cl6", call_id: "call_9871", customer_id: null, customer_phone: "+447700567890", booking_id: null, call_outcome: "no_action", transcript_summary: "Asked about wheelchair-accessible vehicle availability, no booking made.", started_at: iso(-140 * min), ended_at: iso(-138 * min), duration_seconds: 96 },
  { id: "cl7", call_id: "call_9860", customer_id: null, customer_phone: "+447700678901", booking_id: null, call_outcome: "transferred", transcript_summary: "Caller requested a fare dispute, transferred to a human dispatcher.", started_at: iso(-180 * min), ended_at: iso(-176 * min), duration_seconds: 210 },
];

export const mockFareQuotes: FareQuote[] = [
  { id: "fq1", customer_id: "c1", booking_id: "b1", pickup_address: "24 Baker Street, London", dropoff_address: "Heathrow Airport, Terminal 5", pickup_datetime: iso(25 * min), passengers: 1, vehicle_type: "standard", estimated_fare: 58.5, currency: "GBP", created_at: iso(-18 * min) },
  { id: "fq2", customer_id: "c2", booking_id: "b2", pickup_address: "8 Canary Wharf, London", dropoff_address: "Gatwick Airport", pickup_datetime: iso(70 * min), passengers: 2, vehicle_type: "suv", estimated_fare: 82.0, currency: "GBP", created_at: iso(-50 * min) },
  { id: "fq3", customer_id: null, booking_id: null, pickup_address: "Euston Station, London", dropoff_address: "Wembley Stadium, London", pickup_datetime: iso(200 * min), passengers: 4, vehicle_type: "van", estimated_fare: 35.0, currency: "GBP", created_at: iso(-145 * min) },
];
