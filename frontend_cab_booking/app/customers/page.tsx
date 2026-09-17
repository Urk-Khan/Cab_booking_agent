import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import { getCustomers, getBookings } from "@/lib/data";
import { formatPhone, formatDateTime } from "@/lib/format";

// See app/page.tsx for why this is needed — without it this page is frozen at build time.
export const dynamic = "force-dynamic";

export default async function CustomersPage() {
  const [customers, bookings] = await Promise.all([getCustomers(), getBookings()]);

  const tripCount = (id: string) => bookings.filter((b) => b.customer_id === id).length;
  const lastTrip = (id: string) => {
    const trips = bookings
      .filter((b) => b.customer_id === id)
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return trips[0]?.created_at ?? null;
  };

  return (
    <div>
      <PageHeader
        title="Customers"
        description={`${customers.length} customers on record, sourced from calls handled by the voice agent.`}
      />

      <Panel title="All customers">
        <div className="overflow-x-auto">
          <table className="w-full text-[13px] min-w-[700px]">
            <thead>
              <tr className="text-left text-muted border-b border-line">
                <th className="font-medium px-5 py-2.5">Name</th>
                <th className="font-medium px-5 py-2.5">Phone</th>
                <th className="font-medium px-5 py-2.5">Home address</th>
                <th className="font-medium px-5 py-2.5">Trips</th>
                <th className="font-medium px-5 py-2.5">Last trip</th>
              </tr>
            </thead>
            <tbody>
              {customers.map((c) => (
                <tr key={c.id} className="border-b border-line last:border-0 hover:bg-panel2/40">
                  <td className="px-5 py-3">{c.name}</td>
                  <td className="px-5 py-3 font-mono text-[12px] text-muted">{formatPhone(c.phone)}</td>
                  <td className="px-5 py-3 text-muted max-w-[240px] truncate">
                    {c.address ?? <span className="text-faint">—</span>}
                  </td>
                  <td className="px-5 py-3">{tripCount(c.id)}</td>
                  <td className="px-5 py-3 text-muted whitespace-nowrap">
                    {lastTrip(c.id) ? formatDateTime(lastTrip(c.id) as string) : "—"}
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
