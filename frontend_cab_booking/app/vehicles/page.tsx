import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import StatusBadge from "@/components/StatusBadge";
import { getVehicles, getDrivers } from "@/lib/data";

// See app/page.tsx for why this is needed — without it this page is frozen at build time.
export const dynamic = "force-dynamic";

export default async function VehiclesPage() {
  const [vehicles, drivers] = await Promise.all([getVehicles(), getDrivers()]);
  const driverFor = (vehicleId: string) => drivers.find((d) => d.vehicle_id === vehicleId)?.name ?? null;

  const counts = vehicles.reduce<Record<string, number>>((acc, v) => {
    acc[v.status] = (acc[v.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <PageHeader
        title="Fleet"
        description={`${vehicles.length} vehicles — ${counts.available ?? 0} available, ${counts.busy ?? 0} on a trip, ${counts.maintenance ?? 0} in maintenance.`}
      />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
        {vehicles.map((v) => (
          <div key={v.id} className="border border-line bg-panel rounded-md p-4">
            <div className="flex items-start justify-between mb-3">
              <div>
                <p className="font-mono text-[14px] font-medium">{v.plate_number}</p>
                <p className="text-[12px] text-muted capitalize mt-0.5">{v.vehicle_type}</p>
              </div>
              <StatusBadge status={v.status} />
            </div>
            <div className="flex items-center justify-between text-[12px] text-faint pt-3 border-t border-line">
              <span>Capacity {v.capacity}</span>
              <span>{driverFor(v.id) ?? "No driver assigned"}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
