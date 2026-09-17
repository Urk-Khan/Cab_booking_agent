"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";

const NAV = [
  { href: "/", label: "Overview" },
  { href: "/bookings", label: "Bookings" },
  { href: "/calls", label: "Call log" },
  { href: "/drivers", label: "Drivers" },
  { href: "/vehicles", label: "Fleet" },
  { href: "/customers", label: "Customers" },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="w-[210px] shrink-0 border-r border-line bg-panel flex flex-col">
      <div className="px-5 pt-6 pb-5 border-b border-line">
        <div className="flex items-center gap-2.5">
          <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
            <rect x="1" y="7" width="20" height="9" rx="2" fill="#F2B705" />
            <rect x="4" y="4" width="14" height="6" rx="1.5" fill="#F2B705" />
            <circle cx="6" cy="17" r="2" fill="#12151C" stroke="#F2B705" strokeWidth="1.4" />
            <circle cx="16" cy="17" r="2" fill="#12151C" stroke="#F2B705" strokeWidth="1.4" />
            <rect x="3.5" y="9" width="3" height="2" fill="#12151C" />
            <rect x="9.5" y="9" width="3" height="2" fill="#12151C" />
            <rect x="15.5" y="9" width="3" height="2" fill="#12151C" />
          </svg>
          <span className="font-head font-bold text-[17px] tracking-tight">
            Ashad
          </span>
        </div>
        <p className="text-[11px] text-faint mt-1 font-body">Dispatch console</p>
      </div>

      <nav className="flex-1 py-4 px-3 space-y-0.5">
        {NAV.map((item) => {
          const active =
            item.href === "/" ? pathname === "/" : pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center gap-2.5 px-3 py-2 rounded text-[13.5px] font-medium transition-colors ${
                active
                  ? "bg-panel2 text-ink"
                  : "text-muted hover:text-ink hover:bg-panel2/60"
              }`}
            >
              <span
                className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                  active ? "bg-accent" : "bg-line"
                }`}
              />
              {item.label}
            </Link>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-line">
        <p className="text-[11px] text-faint leading-relaxed font-body">
          Reads from the Supabase schema in{" "}
          <span className="font-mono text-faint">icabbi_taxi_schema.sql</span>
        </p>
      </div>
    </aside>
  );
}
