"use client";

import { useState } from "react";
import { AlertTriangle, Quote } from "lucide-react";
import type { Evidence } from "@/lib/types";
import { cn, parseTimestamp } from "@/lib/utils";
import { usePlayer } from "./PlayerContext";

/**
 * The rubric, made interactive — and now auditable.
 *
 * Clicking seeks the audio. The caret opens the verification working: how the
 * quote was checked and what each check scored. That matters because "verified"
 * is two separate questions, and most systems only ask the first:
 *
 *   span match   — does this quote actually occur in the cited turn?
 *   support      — does it *justify the claim being made*?
 *
 * A real quote that does not support its claim is the failure the brief scores
 * NEGATIVELY, and it is invisible behind a single green tick. Showing both
 * numbers is what makes the verdict inspectable rather than asserted.
 */
export default function EvidenceChip({ evidence }: { evidence: Evidence | null }) {
  const { seekTo } = usePlayer();
  const [open, setOpen] = useState(false);

  if (!evidence) {
    return (
      <span className="inline-flex items-center gap-1 rounded border border-dashed border-[var(--hairline)] px-2 py-0.5 font-mono text-xs text-[var(--ink-3)]">
        no evidence
      </span>
    );
  }

  const { timestamp, quote, verified, match_score, support_score, reason } = evidence;
  // "none" method means this claim type is span-only by design: the turn was
  // chosen by our own arithmetic, so entailment-checking it is circular.
  const spanOnly = support_score === 0 && verified;

  // `flex` + `min-w-0`, not `inline-flex`. An inline-flex box sizes to its
  // content, so `max-w-full` on the chip inside resolves against a box that has
  // ALREADY overflowed — the quote then pushes the chip and the "why?" button
  // straight through the right edge of the card. Constraining at the root and
  // letting the quote be the only thing that shrinks is what keeps the "why?"
  // buttons on a single right-hand edge down the panel.
  return (
    <span className="flex w-full min-w-0 flex-col gap-1">
      <span className="flex min-w-0 items-center gap-1.5">
        <button
          type="button" onClick={() => seekTo(parseTimestamp(timestamp))}
          title={`Jump to ${timestamp} — "${quote}"`}
          className={cn(
            "flex min-w-0 flex-1 items-center gap-1.5 rounded border px-2 py-1 text-left font-mono text-xs transition hover:brightness-110",
            verified
              ? " border-[var(--good)]/50 bg-[var(--good)]/10 text-[var(--good)]"
              : " border-[var(--critical)]/50 bg-[var(--critical)]/10 text-[var(--critical)]",
          )}
        >
          {verified ? (
            <Quote size={11} className="shrink-0" />
          ) : (
            <AlertTriangle size={11} className="shrink-0" />
          )}
          <span className="shrink-0 tabular-nums">{timestamp}</span>
          <span className="min-w-0 flex-1 truncate font-sans italic opacity-80">
            &ldquo;{quote}&rdquo;
          </span>
        </button>

        <button
          type="button" onClick={() => setOpen((v) => !v)}
          aria-expanded={open}
          title="How was this verified?" className="shrink-0 rounded border border-[var(--hairline)] px-1.5 py-1 font-mono text-[10px] text-[var(--ink-3)] transition hover:border-[var(--ink-3)] hover:text-[var(--ink-1)]"
        >
          {open ? "hide" : " why?"}
        </button>
      </span>

      {open && (
        <span className="block rounded border border-[var(--hairline)] bg-[var(--surface-1)] p-2.5 font-mono text-[11px] leading-relaxed">
          <span className="block text-[var(--ink-3)]">
            The model returned turn {evidence.turn_id} — never this text. The
            quote was read back from the transcript, then checked twice:
          </span>

          {/* Two checks, one grid: the labels are different lengths, so laying
              them out inline leaves the two scores at different x-positions and
              the reader has to hunt for the comparison that is the whole point. */}
          <span className="mt-2 grid grid-cols-[minmax(0,1fr)_auto] gap-x-3">
            <span className="text-[var(--ink-3)]">quote occurs in turn</span>
            <span
              className={cn(
                "text-right tabular-nums",
                match_score >= 85 ? " text-[var(--good)]" : " text-[var(--critical)]",
              )}
            >
              {match_score.toFixed(0)}/100
            </span>

            <span className="text-[var(--ink-3)]">supports the claim</span>
            {spanOnly ? (
              <span className="text-right text-[var(--ink-3)]">n/a</span>
            ) : (
              <span
                className={cn(
                  "text-right tabular-nums",
                  support_score >= 42
                    ? " text-[var(--good)]"
                    : " text-[var(--critical)]",
                )}
              >
                {support_score.toFixed(0)}/100
              </span>
            )}
          </span>

          {spanOnly && (
            <span className="mt-1 block text-[var(--ink-3)]">
              Support is not applicable here — this turn was chosen by our own
              arithmetic, so entailment-checking it would be circular.
            </span>
          )}

          <span
            className={cn(
              "mt-2 block font-semibold",
              verified ? " text-[var(--good)]" : " text-[var(--critical)]",
            )}
          >
            {verified ? " VERIFIED" : " REJECTED"}
            {!verified && reason ? ` — ${reason}` : ""}
          </span>
        </span>
      )}
    </span>
  );
}
