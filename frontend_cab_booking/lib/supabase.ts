import { createClient, SupabaseClient } from "@supabase/supabase-js";

// Mirrors supabase_client.py from the voice-agent repo: server-side only,
// uses the service-role key so it bypasses Row Level Security. This client
// must never be imported into a "use client" component — it's used from
// Server Components / Route Handlers only, which is why every data-reading
// page in this dashboard is a Server Component.

let cached: SupabaseClient | null = null;

export function getSupabase(): SupabaseClient | null {
  const url = process.env.SUPABASE_URL;
  const key = process.env.SUPABASE_SERVICE_ROLE_KEY;

  if (!url || !key) return null;
  if (cached) return cached;

  cached = createClient(url, key, {
    auth: { persistSession: false },
  });
  return cached;
}

export const isLiveDataConfigured = () =>
  Boolean(process.env.SUPABASE_URL && process.env.SUPABASE_SERVICE_ROLE_KEY);
