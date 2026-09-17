export type BookingStatus =
  | "pending"
  | "confirmed"
  | "dispatched"
  | "en_route"
  | "in_progress"
  | "completed"
  | "cancelled"
  | "no_show";

export type VehicleStatus = "available" | "busy" | "offline" | "maintenance";
export type DriverStatus = "available" | "busy" | "offline" | "on_break";

export interface Booking {
  id: string;
  booking_ref: string;
  customer_id: string | null;
  passenger_name: string;
  passenger_phone: string;
  pickup_address: string;
  dropoff_address: string;
  pickup_datetime: string;
  passengers: number;
  vehicle_type: string;
  notes: string | null;
  status: BookingStatus;
  vehicle_id: string | null;
  driver_id: string | null;
  fare_amount: number | null;
  fare_currency: string | null;
  cancellation_reason: string | null;
  source: string | null;
  call_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface Customer {
  id: string;
  name: string;
  phone: string;
  email: string | null;
  address: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
}

export interface Vehicle {
  id: string;
  plate_number: string;
  vehicle_type: string;
  capacity: number;
  status: VehicleStatus;
  created_at: string;
  updated_at: string;
}

export interface Driver {
  id: string;
  name: string;
  phone: string;
  license_number: string | null;
  status: DriverStatus;
  rating: number | null;
  vehicle_id: string | null;
  created_at: string;
  updated_at: string;
}

export interface CallLog {
  id: string;
  call_id: string | null;
  customer_id: string | null;
  customer_phone: string | null;
  booking_id: string | null;
  call_outcome: string | null;
  transcript_summary: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
}

export interface FareQuote {
  id: string;
  customer_id: string | null;
  booking_id: string | null;
  pickup_address: string;
  dropoff_address: string;
  pickup_datetime: string | null;
  passengers: number | null;
  vehicle_type: string | null;
  estimated_fare: number | null;
  currency: string | null;
  created_at: string;
}
