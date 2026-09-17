export function formatTime(iso: string): string {
  const d = new Date(iso);
  return d.toLocaleTimeString("en-US", { hour: "numeric", minute: "2-digit" });
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  const now = new Date();
  const sameDay = d.toDateString() === now.toDateString();
  if (sameDay) return `Today, ${formatTime(iso)}`;
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" }) + `, ${formatTime(iso)}`;
}

export function relativeTime(iso: string): string {
  const diffMs = new Date(iso).getTime() - Date.now();
  const diffMin = Math.round(diffMs / 60000);
  const abs = Math.abs(diffMin);
  if (abs < 1) return "now";
  if (abs < 60) return diffMin > 0 ? `in ${abs}m` : `${abs}m ago`;
  const hrs = Math.round(abs / 60);
  return diffMin > 0 ? `in ${hrs}h` : `${hrs}h ago`;
}

export function formatCurrency(amount: number | null, currency = "GBP"): string {
  if (amount === null || amount === undefined) return "—";
  return new Intl.NumberFormat("en-GB", { style: "currency", currency }).format(amount);
}

// UK numbers only (this service operates in the UK only — see prompts.py). E.164 UK numbers
// are +44 followed by 10 digits. This is a best-effort display formatter, not a validator:
// it can't know a number's real regional grouping, so it applies a couple of common UK
// conventions and falls back to a generic split for everything else.
export function formatPhone(phone: string | null): string {
  if (!phone) return "—";
  const m = phone.match(/^\+44(\d{10})$/);
  if (!m) return phone;
  const national = `0${m[1]}`;
  if (national.startsWith("020")) {
    // London: 020 XXXX XXXX
    return `${national.slice(0, 3)} ${national.slice(3, 7)} ${national.slice(7)}`;
  }
  if (national.startsWith("07")) {
    // Mobile: 07XXX XXXXXX
    return `${national.slice(0, 5)} ${national.slice(5)}`;
  }
  // Generic UK landline fallback: 0XXXX XXXXXX
  return `${national.slice(0, 5)} ${national.slice(5)}`;
}

export function formatDuration(seconds: number | null): string {
  if (seconds === null || seconds === undefined) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return m > 0 ? `${m}m ${s}s` : `${s}s`;
}

export function initials(name: string): string {
  return name
    .split(" ")
    .map((p) => p[0])
    .slice(0, 2)
    .join("")
    .toUpperCase();
}
