"use client";

import { useEffect, useRef } from "react";
import type { Turn } from "@/lib/types";
import { cn, formatSeconds } from "@/lib/utils";
import { usePlayer } from "./PlayerContext";

interface Props {
  turns: Turn[];
  /** The change-point-detected mood shift, marked inline in the transcript. */
  shiftTurnId?: number | null;
}

export default function TranscriptPanel({ turns, shiftTurnId }: Props) {
  const { seekTo, currentTime } = usePlayer();
  const scrollRef = useRef<HTMLDivElement>(null);

  const activeTurn = turns.find(
    (t) => currentTime >= t.start_seconds && currentTime < t.end_seconds,
  );
  const activeId = activeTurn?.id ?? null;

  // Follow playback, but only scroll within the panel — never yank the page.
  useEffect(() => {
    if (activeId === null || !scrollRef.current) return;
    const el = scrollRef.current.querySelector(`[data-turn-id="${activeId}"]`);
    el?.scrollIntoView({ block: "nearest", behavior: "smooth" });
  }, [activeId]);

  if (turns.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-[var(--hairline)] p-6 text-sm text-[var(--ink-3)]">
        No transcript stored for this call yet — run the ingestion pipeline.
      </div>
    );
  }

  return (
    <div
      ref={scrollRef}
      className="max-h-[28rem] min-w-0 overflow-y-auto overscroll-contain rounded-lg border border-[var(--hairline)]"
    >
      {turns.map((turn) => {
        const isActive = turn.id === activeId;
        const isShift = shiftTurnId != null && turn.id === shiftTurnId;
        return (
          <button
            type="button" key={turn.id}
            data-turn-id={turn.id}
            onClick={() => seekTo(turn.start_seconds)}
            className={cn(
              // The left border is ALWAYS 2px — transparent on ordinary rows.
              // Adding it only on the marked row would indent that row's text
              // by 2px, breaking the left edge every other row shares.
              "flex w-full gap-3 border-b border-l-2 border-[var(--hairline)] border-l-transparent px-4 py-2.5 text-left text-sm transition last:border-b-0",
              isActive ? "bg-[var(--bar)]/10" : "hover:bg-[var(--rail)]",
              isShift && "border-l-[var(--warning)]",
            )}
          >
            <span className="w-11 shrink-0 pt-0.5 text-right font-mono text-xs tabular-nums text-[var(--ink-3)]">
              {formatSeconds(turn.start_seconds)}
            </span>
            <span
              className={cn(
                "w-[4.5rem] shrink-0 pt-0.5 text-xs font-medium uppercase tracking-wide",
                turn.speaker === "customer"
                  ? "text-[var(--ink-1)]"
                  : "text-[var(--ink-3)]",
              )}
            >
              {turn.speaker}
            </span>
            <p className="min-w-0 flex-1">
              {turn.text}
              {turn.overlapping && (
                <span className="ml-2 rounded bg-[var(--rail)] px-1 py-0.5 font-mono text-[10px] uppercase text-[var(--ink-2)]">
                  crosstalk
                </span>
              )}
              {isShift && (
                <span className="ml-2 rounded bg-[var(--warning)]/20 px-1.5 py-0.5 font-mono text-[10px] uppercase text-[var(--warning)]">
                  ◐ mood shift
                </span>
              )}
            </p>
          </button>
        );
      })}
    </div>
  );
}
