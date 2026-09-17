type Tone = "good" | "bad" | "info" | "warn" | "muted";

const TONE_CLASSES: Record<Tone, string> = {
  good: "text-good bg-good/10 border-good/30",
  bad: "text-bad bg-bad/10 border-bad/30",
  info: "text-info bg-info/10 border-info/30",
  warn: "text-warn bg-warn/10 border-warn/30",
  muted: "text-faint bg-white/5 border-line",
};

const STATUS_TONE: Record<string, Tone> = {
  // bookings
  pending: "warn",
  confirmed: "info",
  dispatched: "info",
  en_route: "info",
  in_progress: "good",
  completed: "good",
  cancelled: "bad",
  no_show: "bad",
  // vehicles / drivers
  available: "good",
  busy: "info",
  offline: "muted",
  maintenance: "warn",
  on_break: "warn",
  // calls
  booking_created: "good",
  booking_updated: "info",
  transferred: "warn",
  no_action: "muted",
};

function label(status: string) {
  return status.replace(/_/g, " ");
}

export default function StatusBadge({ status }: { status: string }) {
  const tone = STATUS_TONE[status] ?? "muted";
  return (
    <span
      className={`inline-flex items-center gap-1.5 border rounded px-2 py-0.5 text-[11.5px] font-medium capitalize ${TONE_CLASSES[tone]}`}
    >
      {label(status)}
    </span>
  );
}
