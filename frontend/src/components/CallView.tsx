"use client";

import Link from "next/link";
import type { CallDetail } from "@/lib/types";
import { cn, formatDateTime, formatSeconds } from "@/lib/utils";
import { PlayerProvider } from "./PlayerContext";
import WaveformPlayer from "./WaveformPlayer";
import TranscriptPanel from "./TranscriptPanel";
import MoodTimeline from "./MoodTimeline";
import AttentionBadge from "./AttentionBadge";
import EvidenceChip from "./EvidenceChip";

const RESOLUTION_TONE: Record<string, string> = {
  resolved: "border-emerald-500/50 bg-emerald-500/10 text-emerald-700 dark:text-emerald-400",
  partial: "border-amber-500/50 bg-amber-500/10 text-amber-700 dark:text-amber-400",
  unresolved: "border-red-500/50 bg-red-500/10 text-red-700 dark:text-red-400",
};

/** A judgment and the citation that earns it, side by side. */
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
    <div className="space-y-1.5">
      <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
        {label}
      </p>
      <div>{value}</div>
      <div>{children}</div>
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
            className="text-sm text-indigo-600 hover:underline dark:text-indigo-400"
          >
            ← {call.customer_name}
          </Link>
          <h1 className="mt-1 text-2xl font-semibold">Call {call.id}</h1>
          <p className="mt-1 text-sm text-neutral-500">
            {formatDateTime(call.started_at)} · {formatSeconds(call.duration_seconds)} ·
            agent {call.agent_name} · transcript via {call.transcript_provider}
          </p>
        </div>

        <WaveformPlayer audioUrl={call.audio_url} />

        <div className="grid gap-6 lg:grid-cols-[1fr_22rem]">
          <div className="space-y-6">
            <MoodTimeline turns={call.turns} shiftTurnId={call.mood_shift_turn_id} />
            <TranscriptPanel turns={call.turns} shiftTurnId={call.mood_shift_turn_id} />
          </div>

          <aside className="space-y-6">
            <div className="space-y-5 rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
              <Claim
                label="Intent"
                value={
                  <p className="text-sm">
                    {call.intent_label ?? (
                      <span className="text-neutral-400">not analysed</span>
                    )}
                  </p>
                }
              >
                <EvidenceChip evidence={call.intent_evidence} />
              </Claim>

              <Claim
                label="Resolution"
                value={
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
                    <span className="text-sm text-neutral-400">not analysed</span>
                  )
                }
              >
                <EvidenceChip evidence={call.resolution_evidence} />
              </Claim>

              <Claim
                label="Mood shift"
                value={
                  <p className="text-sm">
                    {call.mood_shift_turn_id !== null ? (
                      `Detected at turn ${call.mood_shift_turn_id}`
                    ) : (
                      <span className="text-neutral-400">no shift detected</span>
                    )}
                  </p>
                }
              >
                <EvidenceChip evidence={call.mood_shift_evidence} />
              </Claim>

              <div className="space-y-1.5">
                <p className="text-xs font-semibold uppercase tracking-wide text-neutral-500">
                  Summary
                </p>
                <p className="text-sm leading-relaxed">
                  {call.summary ?? (
                    <span className="text-neutral-400">not analysed</span>
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
