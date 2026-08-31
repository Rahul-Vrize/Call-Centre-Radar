"use client";

import { useState } from "react";
import Link from "next/link";
import { AlertTriangle } from "lucide-react";
import type { IssueBar } from "@/lib/types";
import { cn } from "@/lib/utils";

/**
 * Issue volume with resolution rate as a direct label.
 *
 * Form: horizontal bars. The job is magnitude comparison across ten named
 * categories with long labels — a horizontal bar reads those labels without
 * rotation, and sorting by volume makes the ranking the shape of the chart.
 *
 * Colour: NOT categorical. Ten issues are not ten identities that need telling
 * apart; they are one measure with a state attached. So one hue carries
 * magnitude and the reserved `critical` status colour marks the exception —
 * which is the only thing on this chart a manager needs to act on.
 *
 * Both colours validated together against both surfaces: worst-pair CVD ΔE 23.8
 * light / 25.7 dark against an ≥8 target, contrast ≥3:1 in both modes.
 *
 * Status colour never carries meaning alone: every flagged bar also gets a
 * warning glyph and its resolution percentage as a direct label.
 */
export default function IssueBars({
  issues,
  baseline,
}: {
  issues: IssueBar[];
  baseline: number;
}) {
  const [hovered, setHovered] = useState<number | null>(null);
  const max = Math.max(...issues.map((i) => i.call_count), 1);

  return (
    <div className="space-y-1.5">
      {issues.map((issue) => {
        const pct = (issue.call_count / max) * 100;
        const active = hovered === issue.cluster_id;
        return (
          <Link
            key={issue.cluster_id}
            href={`/trends/${issue.cluster_id}`}
            onMouseEnter={() => setHovered(issue.cluster_id)}
            onMouseLeave={() => setHovered(null)}
            className="group grid grid-cols-[minmax(0,11rem)_1fr_auto] items-center gap-3 rounded px-1 py-0.5 transition-colors hover:bg-[var(--rail)]"
          >
            <span className="truncate text-[13px] text-[var(--ink-2)] group-hover:text-[var(--ink-1)]">
              {issue.label}
            </span>

            <span className="relative flex h-4 items-center">
              <span
                style={{ width: `${pct}%` }}
                className={cn(
                  // 4px rounded data-end, anchored to the baseline at left
                  "h-2 rounded-r-[4px] transition-[filter]",
                  issue.below_baseline ? "bg-[var(--critical)]" : " bg-[var(--bar)]",
                  active && " brightness-110",
                )}
              />
              {active && (
                <span className="pointer-events-none absolute left-2 top-[-1.9rem] z-10 whitespace-nowrap rounded border border-[var(--hairline)] bg-[var(--surface-2)] px-2 py-1 text-[11px] tabular-nums text-[var(--ink-1)] shadow-sm">
                  {issue.call_count} calls · {(issue.resolution_rate * 100).toFixed(0)}%
                  resolved · attention {issue.avg_attention.toFixed(1)}
                </span>
              )}
            </span>

            <span className="flex items-center gap-1.5 font-mono text-[12px] tabular-nums">
              <span className="w-9 text-right text-[var(--ink-3)]">
                {issue.call_count}
              </span>
              <span
                className={cn(
                  "flex w-16 items-center justify-end gap-1",
                  issue.below_baseline
                    ? "text-[var(--critical)]"
                    : " text-[var(--ink-3)]",
                )}
              >
                {issue.below_baseline && <AlertTriangle size={11} aria-hidden />}
                {(issue.resolution_rate * 100).toFixed(0)}%
              </span>
            </span>
          </Link>
        );
      })}

      <p className="pt-2 text-[11px] text-[var(--ink-3)]">
        Bar length is call volume. Percentage is resolution rate; red marks an
        issue resolving more than 5 points below the{" "}
        {(baseline * 100).toFixed(0)}% average.
      </p>
    </div>
  );
}
