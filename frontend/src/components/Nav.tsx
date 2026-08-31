"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Gauge, Headphones, PhoneCall, Radar, TrendingUp, Upload, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Overview", icon: Gauge },
  { href: "/attention", label: "Attention", icon: Activity },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/trends", label: "Trends", icon: TrendingUp },
  { href: "/agents", label: "Agents", icon: Headphones },
  { href: "/repeat-contacts", label: "Repeats", icon: PhoneCall },
  { href: "/ingest", label: "Analyse a call", icon: Upload },
] as const;

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-[var(--hairline)] bg-[var(--page)]/85 backdrop-blur">
      <nav className="mx-auto flex max-w-6xl flex-wrap items-center gap-1 px-6 py-3">
        <Link href="/" className="mr-6 flex items-center gap-2 font-semibold">
          <Radar size={18} className="text-[var(--bar)]" />
          Call-Centre Radar
        </Link>
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              aria-current={active ? "page" : undefined}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition-colors",
                active
                  ? "bg-[var(--rail)] font-medium text-[var(--ink-1)]"
                  : "text-[var(--ink-3)] hover:bg-[var(--rail)] hover:text-[var(--ink-1)]",
              )}
            >
              <Icon size={15} />
              {label}
            </Link>
          );
        })}
      </nav>
    </header>
  );
}
