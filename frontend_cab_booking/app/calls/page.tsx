import PageHeader from "@/components/PageHeader";
import Panel from "@/components/Panel";
import StatusBadge from "@/components/StatusBadge";
import { getCallLogs, getBookings } from "@/lib/data";
import { formatDateTime, formatDuration, formatPhone } from "@/lib/format";

// See app/page.tsx for why this is needed — without it this page is frozen at build time.
export const dynamic = "force-dynamic";

export default async function CallsPage() {
  const [calls, bookings] = await Promise.all([getCallLogs(), getBookings()]);
  const bookingRef = (id: string | null) => bookings.find((b) => b.id === id)?.booking_ref ?? null;

  const sorted = [...calls].sort(
    (a, b) => new Date(b.started_at).getTime() - new Date(a.started_at).getTime()
  );

  return (
    <div>
      <PageHeader
        title="Call log"
        description="Every inbound call the voice agent handled, what it was about, and what it resulted in."
      />

      <Panel title="Calls">
        <ul className="divide-y divide-line">
          {sorted.map((c) => (
            <li key={c.id} className="px-5 py-4 hover:bg-panel2/40">
              <div className="flex items-start justify-between gap-4 mb-2">
                <div className="flex items-center gap-3">
                  <span className="font-mono text-[12.5px] text-ink">{formatPhone(c.customer_phone)}</span>
                  <span className="font-mono text-[11px] text-faint">{c.call_id}</span>
                </div>
                <div className="flex items-center gap-3 shrink-0">
                  <span className="text-[11.5px] text-faint whitespace-nowrap">
                    {formatDateTime(c.started_at)}
                  </span>
                  <span className="text-[11.5px] text-faint whitespace-nowrap">
                    {formatDuration(c.duration_seconds)}
                  </span>
                </div>
              </div>
              <p className="text-[13px] text-ink/90 leading-relaxed mb-2 max-w-[70ch]">
                {c.transcript_summary ?? "No summary recorded."}
              </p>
              <div className="flex items-center gap-2">
                {c.call_outcome && <StatusBadge status={c.call_outcome} />}
                {bookingRef(c.booking_id) && (
                  <span className="font-mono text-[11.5px] text-accent">
                    → {bookingRef(c.booking_id)}
                  </span>
                )}
              </div>
            </li>
          ))}
        </ul>
      </Panel>
    </div>
  );
}
