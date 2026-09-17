export default function LiveBar({ demo, phoneNumber }: { demo: boolean; phoneNumber: string }) {
  return (
    <div className="h-11 border-b border-line bg-panel/60 flex items-center justify-between px-8 shrink-0">
      <div className="flex items-center gap-2">
        <span className="relative flex h-2 w-2">
          <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-good opacity-60" />
          <span className="relative inline-flex rounded-full h-2 w-2 bg-good" />
        </span>
        <span className="text-[12.5px] text-muted">
          Voice agent listening on <span className="font-mono text-ink">{phoneNumber}</span>
        </span>
      </div>
      {demo && (
        <span className="text-[10.5px] font-medium tracking-wide text-warn border border-warn/40 bg-warn/10 rounded px-2 py-0.5">
          Demo data — set SUPABASE_URL to go live
        </span>
      )}
    </div>
  );
}
