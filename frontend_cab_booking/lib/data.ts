import { getSupabase, isLiveDataConfigured } from "./supabase";
import {
  mockBookings,
  mockCustomers,
  mockVehicles,
  mockDrivers,
  mockCallLogs,
  mockFareQuotes,
} from "./mock-data";
import type { Booking, Customer, Vehicle, Driver, CallLog, FareQuote } from "./types";

export const usingLiveData = isLiveDataConfigured();

export async function getBookings(): Promise<Booking[]> {
  const sb = getSupabase();
  if (!sb) return mockBookings;
  const { data, error } = await sb
    .from("bookings")
    .select("*")
    .order("pickup_datetime", { ascending: true });
  if (error || !data) {
    if (error) console.error("Supabase query error (bookings):", error.message);
    return mockBookings;
  }
  return data as Booking[];
}

export async function getCustomers(): Promise<Customer[]> {
  const sb = getSupabase();
  if (!sb) return mockCustomers;
  const { data, error } = await sb
    .from("customers")
    .select("*")
    .order("created_at", { ascending: false });
  if (error || !data) return mockCustomers;
  return data as Customer[];
}

export async function getVehicles(): Promise<Vehicle[]> {
  const sb = getSupabase();
  if (!sb) return mockVehicles;
  const { data, error } = await sb
    .from("vehicles")
    .select("*")
    .order("plate_number", { ascending: true });
  if (error || !data) return mockVehicles;
  return data as Vehicle[];
}

export async function getDrivers(): Promise<Driver[]> {
  const sb = getSupabase();
  if (!sb) return mockDrivers;
  const { data, error } = await sb
    .from("drivers")
    .select("*")
    .order("name", { ascending: true });
  if (error || !data) return mockDrivers;
  return data as Driver[];
}

export async function getCallLogs(): Promise<CallLog[]> {
  const sb = getSupabase();
  if (!sb) return mockCallLogs;
  const { data, error } = await sb
    .from("call_logs")
    .select("*")
    .order("started_at", { ascending: false });
  if (error || !data) return mockCallLogs;
  return data as CallLog[];
}

export async function getFareQuotes(): Promise<FareQuote[]> {
  const sb = getSupabase();
  if (!sb) return mockFareQuotes;
  const { data, error } = await sb
    .from("fare_quotes")
    .select("*")
    .order("created_at", { ascending: false });
  if (error || !data) return mockFareQuotes;
  return data as FareQuote[];
}
