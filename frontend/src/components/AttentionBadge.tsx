"use client";

import type { AttentionFactor } from "@/lib/types";
import { attentionTone, cn } from "@/lib/utils";
import EvidenceChip from "./EvidenceChip";

interface Props {
  score: number | null;
  factors?: AttentionFactor[];
}

/**
 * The 0-100 score with its arithmetic laid open.
 *
 * Two things this shows that a bare number cannot:
 *
 * 1. **Every contributing factor and its weight**, so the score reconstructs in
 *    front of the reader. It is computed in attention_score.py from published
 *    weights — the model narrates what went wrong, it never supplies the number.
 *
 * 2. **What the score would be without each factor.** Subtracting one factor's
 *    contribution answers "what is actually driving this?" — the question a
 *    manager has when deciding whether a call is worth ten minutes. It needs no
 *    causal inference and no extra data: the weights are additive by
 *    construction, so removing one is subtraction.
 */
export default function AttentionBadge({ score, factors = [] }: Props) {
  const total = score ?? 0;

  // Sorted heaviest-first so the biggest driver is the first thing read.
  const ranked = [...factors].sort((a, b) => b.weight - a.weight);

  return (
    <div className="rounded-lg border border-[var(--hairline)] p-4">
      <div className="flex items-baseline gap-3">
        <span
          className={cn(
            "rounded-md border px-3 py-1 font-mono text-2xl font-semibold tabular-nums",
            attentionTone(score),
          )}
        >
          {score ?? "—"}
        </span>
        <span className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-2)]">
          needs-attention score
        </span>
      </div>

      {ranked.length > 0 && (
        <>
          {/* One grid, not a stack of flex rows. A factor label long enough to
              wrap ("repeat contact — 2 earlier calls about this same issue")
              drags a flex sibling out of line with the rows above it; grid
              columns are shared across every row, so the points, the label and
              the counterfactual each hold a single edge no matter how the
              middle column wraps. */}
          <ul className="mt-4 grid grid-cols-[2.25rem_minmax(0,1fr)_auto] items-baseline gap-x-2 gap-y-2.5">
            {ranked.map((f) => {
              const points = Math.round(f.weight * 100);
              return (
                <li key={f.factor} className="col-span-3 grid grid-cols-subgrid">
                  <span className="text-right font-mono text-xs tabular-nums text-[var(--ink-3)]">
                    +{points}
                  </span>
                  <span className="text-sm">
                    {f.factor}
                    {f.evidence && (
                      <span className="mt-1.5 block">
                        <EvidenceChip evidence={f.evidence} />
                      </span>
                    )}
                  </span>
                  <span
                    className="whitespace-nowrap font-mono text-[11px] tabular-nums text-[var(--ink-3)]" title={`Removing this factor would leave a score of ${total - points}`}
                  >
                    → {total - points} without
                  </span>
                </li>
              );
            })}

            <li className="col-span-3 mt-1 grid grid-cols-subgrid border-t border-[var(--hairline)] pt-2">
              <span className="text-right font-mono text-xs font-semibold tabular-nums">
                {total}
              </span>
              <span className="text-sm text-[var(--ink-2)]">total</span>
            </li>
          </ul>

          <p className="mt-2 text-[11px] text-[var(--ink-3)]">
            Weights are fixed and published in{" "}
            <code className="font-mono">attention_score.py</code>; the score is
            their sum. &ldquo;Without&rdquo; shows what would remain if that one
            factor did not apply.
          </p>
        </>
      )}
    </div>
  );
}
