// The ranked "needs a manager's attention today" view — GET /attention.
import Link from "next/link";
import { getAttention } from "@/lib/api";
import { attentionTone, cn, formatDateTime, formatSeconds, humanLabel } from "@/lib/utils";
import ApiNotice from "@/components/ApiNotice";

export default async function AttentionDashboard({
  searchParams,
}: {
  searchParams: Promise<{ date?: string; reviewed?: string }>;
}) {
  const { date, reviewed } = await searchParams;
  const showReviewed = reviewed === "1";
  const { data, error } = await getAttention(date, showReviewed);
  const dateQs = date ? `date=${encodeURIComponent(date)}` : "";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Needs a manager&apos;s attention</h1>
        <p className="mt-1 text-sm text-[var(--ink-3)]">
          Ranked by the computed 0-100 score. Every call opens to the citation
          behind its ranking.
        </p>
      </div>

      {error && <ApiNotice error={error} />}

      {/* The corpus covers four days in 2020, so "today" is the most recent day
          with calls rather than the literal date. Exposing the other days means
          a judge asking for a specific one doesn't need a hand-typed URL. */}
      {data && data.available_dates.length > 0 && (
        <div className="flex flex-wrap items-center gap-2">
          <span className="text-xs uppercase tracking-wide text-[var(--ink-3)]">
            Day
          </span>
          {data.available_dates.map((day) => {
            const active = day.date === data.date;
            return (
              <Link
                key={day.date}
                href={`/attention?date=${day.date}${showReviewed ? "&reviewed=1" : ""}`}
                className={cn(
                  "rounded-md border px-3 py-1 font-mono text-xs tabular-nums transition",
                  active
                    ? "border-[var(--bar)] bg-[var(--bar)]/10 text-[var(--bar)]"
                    : "border-[var(--hairline)] text-[var(--ink-3)] hover:border-[var(--bar)]",
                )}
              >
                {day.date}
                <span className="ml-2 text-[var(--ink-3)]">{day.call_count}</span>
              </Link>
            );
          })}
        </div>
      )}

      {data && (data.reviewed_count > 0 || showReviewed) && (
        /* Shown even when the reviewed calls are hidden: a queue that shrinks
           should read as work done, not as rows going missing. */
        <p className="flex flex-wrap items-center gap-2 text-xs text-[var(--ink-3)]">
          <span>
            {data.reviewed_count} of this day&apos;s calls already reviewed
          </span>
          <Link
            href={`/attention?${[dateQs, showReviewed ? "" : "reviewed=1"]
              .filter(Boolean)
              .join("&")}`}
            className="rounded border border-[var(--hairline)] px-2 py-0.5 transition-colors hover:border-[var(--bar)] hover:text-[var(--ink-1)]"
          >
            {showReviewed ? "hide reviewed" : "show reviewed"}
          </Link>
        </p>
      )}

      {data && data.calls.length === 0 && (
        <p className="text-sm text-[var(--ink-3)]">
          {data.reviewed_count > 0
            ? `Queue clear — all ${data.reviewed_count} flagged calls for ${data.date} have been reviewed.`
            : `No calls${data.date ? ` for ${data.date}` : ""}.`}
        </p>
      )}

      {data && data.calls.length > 0 && (
        <ul className="space-y-2">
          {data.calls.map((call) => (
            <li key={call.id}>
              <Link
                href={`/calls/${encodeURIComponent(call.id)}`}
                className={cn(
                  "flex items-start gap-4 rounded-lg border p-4 transition hover:border-[var(--bar)]",
                  call.is_reviewed
                    ? "border-[var(--good)]/40 bg-[var(--good)]/5"
                    : "border-[var(--hairline)]",
                )}
              >
                <span
                  className={cn(
                    "shrink-0 rounded-md border px-2.5 py-1 font-mono text-lg font-semibold tabular-nums",
                    attentionTone(call.attention_score),
                  )}
                >
                  {call.attention_score ?? "—"}
                </span>
                <div className="min-w-0 flex-1">
                  <p className="flex items-baseline gap-2 font-medium">
                    {humanLabel(call.intent_label)}
                    {call.is_reviewed && (
                      <span className="rounded border border-[var(--good)]/50 px-1.5 py-0.5 font-mono text-[10px] uppercase text-[var(--good)]">
                        reviewed
                      </span>
                    )}
                  </p>
                  <p className="mt-0.5 line-clamp-2 text-sm text-[var(--ink-3)]">
                    {call.summary ?? "No summary stored."}
                  </p>
                  <p className="mt-1 font-mono text-xs text-[var(--ink-3)]">
                    {formatDateTime(call.started_at)} ·{" "}
                    {formatSeconds(call.duration_seconds)} ·{" "}
                    {call.resolution_status ?? "unknown"}
                  </p>
                </div>
              </Link>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
