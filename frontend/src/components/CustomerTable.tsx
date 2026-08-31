"use client";

import { useMemo, useState } from "react";
import Link from "next/link";
import { Search } from "lucide-react";
import type { Customer } from "@/lib/types";
import { formatDateTime } from "@/lib/utils";

/**
 * 100 customers is too many to scan and too few to paginate, so filtering
 * happens client-side over the already-loaded list — instant, no round trip,
 * and no server state to get out of sync.
 */
export default function CustomerTable({ customers }: { customers: Customer[] }) {
  const [query, setQuery] = useState("");

  const visible = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return customers;
    return customers.filter((c) => c.name.toLowerCase().includes(q));
  }, [customers, query]);

  return (
    <div className="space-y-4">
      <div className="relative max-w-sm">
        <Search
          size={15}
          className="pointer-events-none absolute left-3 top-1/2 -translate-y-1/2 text-[var(--ink-3)]"
        />
        <input
          type="search"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search by name…"
          aria-label="Search customers by name"
          className="w-full rounded-md border border-[var(--hairline)] bg-transparent py-2 pl-9 pr-3 text-sm outline-none placeholder:text-[var(--ink-3)] focus:border-[var(--bar)]"
        />
      </div>

      <p className="text-sm text-[var(--ink-3)]">
        {visible.length === customers.length
          ? `${customers.length} customers`
          : `${visible.length} of ${customers.length} customers`}
      </p>

      {visible.length === 0 ? (
        <p className="text-sm text-[var(--ink-3)]">
          No customer matches “{query}”.
        </p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-[var(--hairline)]">
          <table className="w-full text-sm">
            <thead className="border-b border-[var(--hairline)] bg-[var(--rail)] text-left text-xs uppercase tracking-wide text-[var(--ink-3)]">
              <tr>
                <th className="px-4 py-2.5 font-medium">Name</th>
                <th className="px-4 py-2.5 font-medium">Calls</th>
                <th className="px-4 py-2.5 font-medium">Last contact</th>
              </tr>
            </thead>
            <tbody>
              {visible.map((c) => (
                <tr
                  key={c.id}
                  className="border-b border-[var(--hairline)] last:border-b-0 hover:bg-[var(--rail)]"
                >
                  <td className="px-4 py-2.5">
                    <Link
                      href={`/customers/${encodeURIComponent(c.id)}`}
                      className="font-medium text-[var(--bar)] hover:underline"
                    >
                      {c.name}
                    </Link>
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">{c.call_count}</td>
                  <td className="px-4 py-2.5 text-[var(--ink-3)]">
                    {c.last_contact ? formatDateTime(c.last_contact) : "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
