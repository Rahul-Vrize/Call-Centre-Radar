"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { Activity, Headphones, Radar, TrendingUp, Upload, Users } from "lucide-react";
import { cn } from "@/lib/utils";

const LINKS = [
  { href: "/", label: "Attention", icon: Activity },
  { href: "/customers", label: "Customers", icon: Users },
  { href: "/trends", label: "Trends", icon: TrendingUp },
  { href: "/agents", label: "Agents", icon: Headphones },
  { href: "/ingest", label: "Analyse a call", icon: Upload },
] as const;

export default function Nav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-10 border-b border-neutral-200 bg-white/80 backdrop-blur dark:border-neutral-800 dark:bg-neutral-950/80">
      <nav className="mx-auto flex max-w-6xl items-center gap-1 px-6 py-3">
        <Link href="/" className="mr-6 flex items-center gap-2 font-semibold">
          <Radar size={18} className="text-indigo-500" />
          Call-Centre Radar
        </Link>
        {LINKS.map(({ href, label, icon: Icon }) => {
          const active =
            href === "/" ? pathname === "/" : pathname.startsWith(href);
          return (
            <Link
              key={href}
              href={href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-3 py-1.5 text-sm transition",
                active
                  ? "bg-indigo-500/10 font-medium text-indigo-600 dark:text-indigo-400"
                  : "text-neutral-600 hover:bg-neutral-100 dark:text-neutral-400 dark:hover:bg-neutral-900",
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
