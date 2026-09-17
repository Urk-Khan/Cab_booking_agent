import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import StatusBadge from "@/components/StatusBadge";
import { getBookings, getDrivers, getVehicles } from "@/lib/data";
import { formatCurrency, formatDateTime, formatPhone } from "@/lib/format";

// See app/page.tsx for why this is needed — without it this page is frozen at build time.
export const dynamic = "force-dynamic";

export default async function BookingsPage() {
  const [bookings, drivers, vehicles] = await Promise.all([
    getBookings(),
    getDrivers(),
    getVehicles(),
  ]);

  const driverName = (id: string | null) => drivers.find((d) => d.id === id)?.name ?? "—";
  const plate = (id: string | null) => vehicles.find((v) => v.id === id)?.plate_number ?? "—";

  const sorted = [...bookings].sort(
    (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()
  );

  return (
    <div>
      <PageHeader
        title="Bookings"
        description={`${bookings.length} bookings total — every row is a call the voice agent turned into (or attempted) a trip.`}
      />

      <Panel title="All bookings">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] min-w-[900px]">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="font-medium px-5 py-2.5">Ref</th>
                <th className="font-medium px-5 py-2.5">Passenger</th>
                <th className="font-medium px-5 py-2.5">Pickup → Drop-off</th>
                <th className="font-medium px-5 py-2.5">Pickup time</th>
                <th className="font-medium px-5 py-2.5">Driver / vehicle</th>
                <th className="font-medium px-5 py-2.5">Fare</th>
                <th className="font-medium px-5 py-2.5">Status</th>
              </tr>
            </thead>
            <tbody>
              {sorted.map((b) => (
                <tr key={b.id} className="border-b border-line last:border-0 hover:bg-panel2/40 align-top">
                  <td className="px-5 py-3 font-mono text-[12px] text-accent whitespace-nowrap">
                    {b.booking_ref}
                  </td>
                  <td className="px-5 py-3">
                    <div>{b.passenger_name}</div>
                    <div className="text-[11.5px] text-faint font-mono">{formatPhone(b.passenger_phone)}</div>
                  </td>
                  <td className="px-5 py-3 text-muted max-w-[260px]">
                    <div className="truncate">{b.pickup_address}</div>
                    <div className="truncate text-faint">→ {b.dropoff_address}</div>
                  </td>
                  <td className="px-5 py-3 whitespace-nowrap text-muted">
                    {formatDateTime(b.pickup_datetime)}
                  </td>
                  <td className="px-5 py-3 whitespace-nowrap">
                    {b.driver_id ? (
                      <>
                        <div>{driverName(b.driver_id)}</div>
                        <div className="text-[11.5px] text-faint font-mono">{plate(b.vehicle_id)}</div>
                      </>
                    ) : (
                      <span className="text-faint">Unassigned</span>
                    )}
                  </td>
                  <td className="px-5 py-3 whitespace-nowrap font-mono text-[12.5px]">
                    {formatCurrency(b.fare_amount, b.fare_currency ?? "GBP")}
                  </td>
                  <td className="px-5 py-3">
                    <StatusBadge status={b.status} />
                    {b.status === "cancelled" && b.cancellation_reason && (
                      <div className="text-[11px] text-faint mt-1 max-w-[160px]">
                        {b.cancellation_reason}
                      </div>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Panel>
    </div>
  );
}
