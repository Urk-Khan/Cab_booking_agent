import PageHeader from "@/components/PageHeader";
import StatCard from "@/components/StatCard";
import Panel from "@/components/Panel";
import StatusBadge from "@/components/StatusBadge";
import Link from "next/link";
import { getBookings, getDrivers, getVehicles, getCallLogs } from "@/lib/data";
import { formatCurrency, formatPhone, relativeTime, formatDuration } from "@/lib/format";

// Without this, Next.js sees no dynamic APIs used and pre-renders this page once at
// build time — every dispatcher would see a frozen snapshot from whenever it was last
// deployed, not live data. force-dynamic makes it re-fetch from Supabase on every request.
export const dynamic = "force-dynamic";

const ACTIVE_STATUSES = ["pending", "confirmed", "dispatched", "en_route", "in_progress"];

export default async function OverviewPage() {
  const [bookings, drivers, vehicles, calls] = await Promise.all([
    getBookings(),
    getDrivers(),
    getVehicles(),
    getCallLogs(),
  ]);

  const todayStart = new Date();
  todayStart.setHours(0, 0, 0, 0);

  const todaysCalls = calls.filter((c) => new Date(c.started_at) >= todayStart);
  const todaysBookings = bookings.filter((b) => new Date(b.created_at) >= todayStart);
  const completedToday = todaysBookings.filter((b) => b.status === "completed");
  const conversionRate =
    todaysCalls.length > 0
      ? Math.round(
          (todaysCalls.filter((c) => c.call_outcome === "booking_created").length /
            todaysCalls.length) *
            100
        )
      : 0;

  const activeBookings = bookings
    .filter((b) => ACTIVE_STATUSES.includes(b.status))
    .sort((a, b) => new Date(a.pickup_datetime).getTime() - new Date(b.pickup_datetime).getTime());

  const avgFare =
    completedToday.length > 0
      ? completedToday.reduce((s, b) => s + (b.fare_amount ?? 0), 0) / completedToday.length
      : null;

  const driversAvailable = drivers.filter((d) => d.status === "available").length;
  const vehiclesAvailable = vehicles.filter((v) => v.status === "available").length;

  return (
    <div>
      <PageHeader
        title="Overview"
        description="Live snapshot of calls, bookings, and fleet availability handled by the voice agent."
      />

      <div className="flex flex-wrap gap-3 mb-6">
        <StatCard label="Calls today" value={String(todaysCalls.length)} accent />
        <StatCard label="Bookings created today" value={String(todaysBookings.length)} />
        <StatCard
          label="Call → booking rate"
          value={`${conversionRate}%`}
          sub={`${todaysCalls.length} calls handled`}
        />
        <StatCard
          label="Avg. completed fare"
          value={avgFare !== null ? formatCurrency(avgFare) : "—"}
          sub={`${completedToday.length} completed today`}
        />
        <StatCard
          label="Fleet available"
          value={`${vehiclesAvailable}/${vehicles.length}`}
          sub={`${driversAvailable} drivers free`}
        />
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-5">
        <div className="lg:col-span-2">
          <Panel
            title="Active bookings"
            action={
              <Link href="/bookings" className="text-[12px] text-accent hover:underline">
                View all
              </Link>
            }
          >
            <table className="w-full text-[13px]">
              <thead>
                <tr className="text-left text-muted border-b border-line">
                  <th className="font-medium px-5 py-2.5">Ref</th>
                  <th className="font-medium px-5 py-2.5">Passenger</th>
                  <th className="font-medium px-5 py-2.5">Route</th>
                  <th className="font-medium px-5 py-2.5">Pickup</th>
                  <th className="font-medium px-5 py-2.5">Status</th>
                </tr>
              </thead>
              <tbody>
                {activeBookings.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-8 text-center text-faint">
                      No active bookings right now.
                    </td>
                  </tr>
                )}
                {activeBookings.slice(0, 7).map((b) => (
                  <tr key={b.id} className="border-b border-line last:border-0 hover:bg-panel2/40">
                    <td className="px-5 py-2.5 font-mono text-[12px] text-accent">
                      {b.booking_ref}
                    </td>
                    <td className="px-5 py-2.5">{b.passenger_name}</td>
                    <td className="px-5 py-2.5 text-muted max-w-[220px] truncate">
                      {b.pickup_address.split(",")[0]} → {b.dropoff_address.split(",")[0]}
                    </td>
                    <td className="px-5 py-2.5 text-muted whitespace-nowrap">
                      {relativeTime(b.pickup_datetime)}
                    </td>
                    <td className="px-5 py-2.5">
                      <StatusBadge status={b.status} />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Panel>
        </div>

        <Panel title="Recent calls">
          <ul className="divide-y divide-line">
            {calls.slice(0, 6).map((c) => (
              <li key={c.id} className="px-5 py-3">
                <div className="flex items-center justify-between mb-1">
                  <span className="font-mono text-[11.5px] text-muted">
                    {formatPhone(c.customer_phone)}
                  </span>
                  <span className="text-[11px] text-faint">{relativeTime(c.started_at)}</span>
                </div>
                <p className="text-[12.5px] text-ink/90 leading-snug line-clamp-2 mb-1.5">
                  {c.transcript_summary ?? "No summary recorded."}
                </p>
                <div className="flex items-center justify-between">
                  {c.call_outcome && <StatusBadge status={c.call_outcome} />}
                  <span className="text-[11px] text-faint">{formatDuration(c.duration_seconds)}</span>
                </div>
              </li>
            ))}
          </ul>
        </Panel>
      </div>
    </div>
  );
}
