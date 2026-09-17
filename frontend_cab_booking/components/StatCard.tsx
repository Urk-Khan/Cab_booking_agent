export default function StatCard({
  label,
  value,
  sub,
  accent = false,
}: {
  label: string;
  value: string;
  sub?: string;
  accent?: boolean;
}) {
  return (
    <div className="border border-line bg-panel rounded-md px-5 py-4 flex-1 min-w-[150px]">
      <p className="text-[11.5px] text-muted mb-1.5">{label}</p>
      <p
        className={`font-head text-[26px] leading-none font-semibold ${
          accent ? "text-accent" : "text-ink"
        }`}
      >
        {value}
      </p>
      {sub && <p className="text-[11.5px] text-faint mt-1.5">{sub}</p>}
    </div>
  );
}
