"use client";

import Link from "next/link";
import type { CallDetail } from "@/lib/types";
import { cn, formatDateTime, formatSeconds, humanLabel } from "@/lib/utils";
import { PlayerProvider } from "./PlayerContext";
import WaveformPlayer from "./WaveformPlayer";
import TranscriptPanel from "./TranscriptPanel";
import MoodTimeline from "./MoodTimeline";
import AttentionBadge from "./AttentionBadge";
import EvidenceChip from "./EvidenceChip";

const RESOLUTION_TONE: Record<string, string> = {
  resolved: "border-[var(--good)]/50 bg-[var(--good)]/10 text-[var(--good)]",
  partial: "border-[var(--warning)]/50 bg-[var(--warning)]/10 text-[var(--warning)]",
  unresolved: "border-[var(--critical)]/50 bg-[var(--critical)]/10 text-[var(--critical)]",
};

/** A judgment and the citation that earns it, stacked on one left edge. */
function Claim({
  label,
  value,
  children,
}: {
  label: string;
  value: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="min-w-0 space-y-1.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-3)]">
        {label}
      </p>
      <div className="min-w-0">{value}</div>
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export default function CallView({ call }: { call: CallDetail }) {
  return (
    <PlayerProvider>
      <div className="space-y-6">
        <div>
          <Link
            href={`/customers/${encodeURIComponent(call.customer_id)}`}
            className="text-sm text-[var(--bar)] hover:underline"
          >
            ← {call.customer_name}
          </Link>
          {/* The heading is the CALL, and a call's name is when it happened and
              who took it. The id is a database key, not a title — it belongs in
              the meta line with the other identifiers. */}
          <h1 className="mt-1 text-2xl font-semibold">
            {formatDateTime(call.started_at)}
          </h1>
          <p className="mt-1 flex flex-wrap items-center gap-x-2 gap-y-1 text-sm text-[var(--ink-3)]">
            <span>{formatSeconds(call.duration_seconds)}</span>
            <span aria-hidden>·</span>
            <span>agent {call.agent_name}</span>
            <span aria-hidden>·</span>
            <span>transcript via {call.transcript_provider}</span>
            <span aria-hidden>·</span>
            <span className="font-mono text-xs">{call.id}</span>
          </p>
        </div>

        <WaveformPlayer audioUrl={call.audio_url} />

        {/* minmax(0,…) on both tracks: a bare `1fr` is `minmax(auto,1fr)`, and
            `auto` refuses to shrink below its content, so a long transcript line
            or a wide chip pushes the whole grid past the viewport. */}
        <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,22rem)]">
          <div className="min-w-0 space-y-6">
            <MoodTimeline turns={call.turns} shiftTurnId={call.mood_shift_turn_id} />
            <TranscriptPanel turns={call.turns} shiftTurnId={call.mood_shift_turn_id} />
          </div>

          <aside className="min-w-0 space-y-6">
            <div className="min-w-0 space-y-5 rounded-lg border border-[var(--hairline)] p-4">
              <Claim
                label="Intent" value={
                  <p className="text-sm">
                    {/* humanLabel, same as the dashboard. The stored value is a
                        snake_case identifier; showing it raw here while the
                        overview shows "Transfer funds"made one call look like
                        two different things depending on which page you were on. */}
                    {call.intent_label ? (
                      humanLabel(call.intent_label)
                    ) : (
                      <span className="text-[var(--ink-3)]">not analysed</span>
                    )}
                  </p>
                }
              >
                <EvidenceChip evidence={call.intent_evidence} />
              </Claim>

              <Claim
                label="Resolution" value={
                  call.resolution_status ? (
                    <span
                      className={cn(
                        "inline-block rounded border px-2 py-0.5 text-xs font-medium uppercase",
                        RESOLUTION_TONE[call.resolution_status],
                      )}
                    >
                      {call.resolution_status}
                    </span>
                  ) : (
                    <span className="text-sm text-[var(--ink-3)]">not analysed</span>
                  )
                }
              >
                <EvidenceChip evidence={call.resolution_evidence} />
              </Claim>

              <Claim
                label="Mood shift" value={
                  <p className="text-sm">
                    {call.mood_shift_turn_id !== null ? (
                      // The turn id is a database key. What a reader needs is
                      // the moment, which the citation already carries.
                      <>
                        Detected at{" "}
                        <span className="font-mono tabular-nums">
                          {call.mood_shift_evidence?.timestamp ?? "—"}
                        </span>
                      </>
                    ) : (
                      <span className="text-[var(--ink-3)]">no shift detected</span>
                    )}
                  </p>
                }
              >
                <EvidenceChip evidence={call.mood_shift_evidence} />
              </Claim>

              <div className="min-w-0 space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-3)]">
                  Summary
                </p>
                <p className="text-sm leading-relaxed">
                  {call.summary ?? (
                    <span className="text-[var(--ink-3)]">not analysed</span>
                  )}
                </p>
              </div>
            </div>

            <AttentionBadge
              score={call.attention_score}
              factors={call.attention_factors}
            />
          </aside>
        </div>
      </div>
    </PlayerProvider>
  );
}
