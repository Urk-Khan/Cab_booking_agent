import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import StatusBadge from "@/components/StatusBadge";
import { getDrivers, getVehicles } from "@/lib/data";
import { formatPhone, initials } from "@/lib/format";

// See app/page.tsx for why this is needed — without it this page is frozen at build time.
export const dynamic = "force-dynamic";

export default async function DriversPage() {
  const [drivers, vehicles] = await Promise.all([getDrivers(), getVehicles()]);
  const plate = (id: string | null) => vehicles.find((v) => v.id === id)?.plate_number ?? null;

  const counts = drivers.reduce<Record<string, number>>((acc, d) => {
    acc[d.status] = (acc[d.status] ?? 0) + 1;
    return acc;
  }, {});

  return (
    <div>
      <PageHeader
        title="Drivers"
        description={`${drivers.length} drivers on record — ${counts.available ?? 0} available right now.`}
      />

      <Panel title="Roster">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] min-w-[700px]">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="font-medium px-5 py-2.5">Driver</th>
                <th className="font-medium px-5 py-2.5">Phone</th>
                <th className="font-medium px-5 py-2.5">License</th>
                <th className="font-medium px-5 py-2.5">Vehicle</th>
                <th className="font-medium px-5 py-2.5">Rating</th>
                <th className="font-medium px-5 py-2.5">Status</th>
              </tr>
            </thead>
            <tbody>
              {drivers.map((d) => (
                <tr key={d.id} className="border-b border-line last:border-0 hover:bg-panel2/40">
                  <td className="px-5 py-3">
                    <div className="flex items-center gap-2.5">
                      <span className="w-7 h-7 rounded-full bg-panel2 border border-line flex items-center justify-center text-[10.5px] font-medium text-muted shrink-0">
                        {initials(d.name)}
                      </span>
                      {d.name}
                    </div>
                  </td>
                  <td className="px-5 py-3 font-mono text-[12px] text-muted">{formatPhone(d.phone)}</td>
                  <td className="px-5 py-3 font-mono text-[12px] text-muted">
                    {d.license_number ?? "—"}
                  </td>
                  <td className="px-5 py-3 font-mono text-[12px]">
                    {plate(d.vehicle_id) ?? <span className="text-faint">Unassigned</span>}
                  </td>
                  <td className="px-5 py-3 text-muted">{d.rating ? d.rating.toFixed(1) : "—"}</td>
                  <td className="px-5 py-3">
                    <StatusBadge status={d.status} />
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
