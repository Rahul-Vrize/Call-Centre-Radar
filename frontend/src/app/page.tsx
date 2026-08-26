// The ranked "needs a manager's attention today" view — GET /attention.
import Link from "next/link";
import { getAttention } from "@/lib/api";
import { attentionTone, cn, formatDateTime, formatSeconds } from "@/lib/utils";
import ApiNotice from "@/components/ApiNotice";

export default async function AttentionDashboard({
  searchParams,
}: {
  searchParams: Promise<{ date?: string }>;
}) {
  const { date } = await searchParams;
  const { data, error } = await getAttention(date);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Needs a manager&apos;s attention</h1>
        <p className="mt-1 text-sm text-neutral-500">
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
          <span className="text-xs uppercase tracking-wide text-neutral-500">
            Day
          </span>
          {data.available_dates.map((day) => {
            const active = day.date === data.date;
            return (
              <Link
                key={day.date}
                href={`/?date=${day.date}`}
                className={cn(
                  "rounded-md border px-3 py-1 font-mono text-xs tabular-nums transition",
                  active
                    ? "border-indigo-500 bg-indigo-500/10 text-indigo-600 dark:text-indigo-400"
                    : "border-neutral-200 text-neutral-500 hover:border-indigo-400 dark:border-neutral-800",
                )}
              >
                {day.date}
                <span className="ml-2 text-neutral-400">{day.call_count}</span>
              </Link>
            );
          })}
        </div>
      )}

      {data && data.calls.length === 0 && (
        <p className="text-sm text-neutral-500">
          No calls{data.date ? ` for ${data.date}` : ""}.
        </p>
      )}

      {data && data.calls.length > 0 && (
        <ul className="space-y-2">
          {data.calls.map((call) => (
            <li key={call.id}>
              <Link
                href={`/calls/${encodeURIComponent(call.id)}`}
                className="flex items-start gap-4 rounded-lg border border-neutral-200 p-4 transition hover:border-indigo-400 dark:border-neutral-800"
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
                  <p className="font-medium">
                    {call.intent_label ?? "Intent not analysed"}
                  </p>
                  <p className="mt-0.5 line-clamp-2 text-sm text-neutral-500">
                    {call.summary ?? "No summary stored."}
                  </p>
                  <p className="mt-1 font-mono text-xs text-neutral-400">
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
