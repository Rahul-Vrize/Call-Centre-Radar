// The control room — GET /overview, one round trip.
//
// Layout follows the operational-dashboard pattern rather than the executive
// one: this is a shift-handover screen for a support manager, so density is a
// feature. Five KPIs across the top (the researched ceiling is 4–6), then the
// exceptions — the only things anyone can act on — then the full issue
// breakdown for context.
//
// Scope is ALL FOUR DAYS. /attention is the per-day view; this page answers
// "what is wrong across the whole corpus", and a day filter here would hide
// two thirds of it.
//
// Interactivity is deliberately minimal. Every number is either final or a
// link; there are no filters to configure before the screen means something,
// because time-to-insight degrades sharply when a frequently-viewed dashboard
// makes you assemble it yourself.
import Link from "next/link";
import { AlertTriangle, ArrowUpRight, GraduationCap, PhoneCall } from "lucide-react";
import { getOverview } from "@/lib/api";
import type { Overview } from "@/lib/types";
import { attentionTone, cn, formatDate, formatSeconds, humanLabel } from "@/lib/utils";
import ApiNotice from "@/components/ApiNotice";
import IssueBars from "@/components/IssueBars";

export const dynamic = "force-dynamic";

function Kpi({
  value,
  label,
  sub,
  tone,
  href,
}: {
  value: string;
  label: string;
  sub: string;
  tone?: "critical" | "good";
  href?: string;
}) {
  const body = (
    <>
      <p
        className={cn(
          "text-[26px] font-semibold leading-none tracking-tight",
          tone === "critical" && " text-[var(--critical)]",
          tone === "good" && " text-[var(--good)]",
        )}
      >
        {value}
      </p>
      <p className="mt-2 text-[11px] font-medium uppercase tracking-[0.08em] text-[var(--ink-2)]">
        {label}
      </p>
      <p className="mt-0.5 text-[11px] text-[var(--ink-3)]">{sub}</p>
    </>
  );

  const shell =
    "block border-l border-[var(--hairline)] px-5 py-1 first:border-l-0 first:pl-0";
  return href ? (
    <Link href={href} className={cn(shell, "group transition-opacity hover:opacity-80")}>
      {body}
    </Link>
  ) : (
    <div className={shell}>{body}</div>
  );
}

/** An exception block. Everything here is something a manager can act on. */
function Exception({
  icon,
  title,
  href,
  children,
}: {
  icon: React.ReactNode;
  title: string;
  href: string;
  children: React.ReactNode;
}) {
  return (
    <section className="border-t border-[var(--hairline)] pt-3 first:border-t-0 first:pt-0">
      <div className="flex items-baseline justify-between gap-3">
        <h3 className="flex items-center gap-1.5 text-[12px] font-semibold uppercase tracking-[0.06em] text-[var(--ink-1)]">
          <span className="text-[var(--critical)]">{icon}</span>
          {title}
        </h3>
        <Link
          href={href}
          className="flex items-center gap-0.5 text-[11px] text-[var(--ink-3)] transition-colors hover:text-[var(--ink-1)]"
        >
          all <ArrowUpRight size={11} />
        </Link>
      </div>
      <div className="mt-2 space-y-1">{children}</div>
    </section>
  );
}

function Row({
  href,
  left,
  right,
}: {
  href: string;
  left: React.ReactNode;
  right: React.ReactNode;
}) {
  return (
    <Link
      href={href}
      className="block rounded px-1.5 py-1 transition-colors hover:bg-[var(--rail)]"
    >
      <span className="block truncate text-[13px] text-[var(--ink-2)]">{left}</span>
      <span className="mt-0.5 block font-mono text-[11px] tabular-nums text-[var(--ink-3)]">
        {right}
      </span>
    </Link>
  );
}

export default async function ControlRoom() {
  const { data, error } = await getOverview();

  if (error || !data) {
    return (
      <div className="space-y-4">
        <h1 className="text-2xl font-semibold">Call-Centre Radar</h1>
        <ApiNotice error={error ?? "No data returned."} />
      </div>
    );
  }

  const k: Overview["kpis"] = data.kpis;

  return (
    <div className="viz-root space-y-7">
      {/* ---- masthead ---------------------------------------------------- */}
      <header className="flex flex-wrap items-end justify-between gap-x-6 gap-y-2 border-b border-[var(--hairline)] pb-5">
        <div>
          <h1 className="text-[19px] font-semibold tracking-tight">
            Every call, with the receipts
          </h1>
          <p className="mt-1 max-w-2xl text-[13px] text-[var(--ink-2)]">
            Every judgment below cites the second it came from. The model is never
            allowed to write a quote — it points at a turn, and the words are
            read back from the transcript.
          </p>
        </div>
        <p className="font-mono text-[11px] tabular-nums text-[var(--ink-3)]">
          {k.calls_analysed.toLocaleString()} calls · {k.hours_of_audio} hrs ·{" "}
          {k.days_covered} days
        </p>
      </header>

      {/* ---- KPI rail ---------------------------------------------------- */}
      <div className="flex flex-wrap gap-y-5">
        <Kpi
          value={`${(k.citation_rate * 100).toFixed(1)}%`}
          label="Evidence verified" sub={`${k.citations_verified.toLocaleString()} of ${k.citations_total.toLocaleString()}`}
          tone="good"
        />
        <Kpi
          value={k.needs_attention.toLocaleString()}
          label="Need a manager" sub="score 30 or higher" tone="critical" href="/attention"
        />
        <Kpi
          value={k.unresolved.toLocaleString()}
          label="Unresolved" sub={`of ${k.calls_analysed.toLocaleString()} analysed`}
        />
        <Kpi
          value={k.repeat_contact_issues.toLocaleString()}
          label="Repeat contacts" sub="3+ calls, same issue" href="/repeat-contacts"
        />
        <Kpi
          value={data.issues.length.toString()}
          label="Issues found" sub="found automatically" href="/trends"
        />
      </div>

      {/* ---- the two things that matter: queue + exceptions -------------- */}
      <div className="grid gap-x-10 gap-y-8 lg:grid-cols-[minmax(0,1fr)_21rem]">
        <section>
          <div className="flex items-baseline justify-between">
            <h2 className="text-[12px] font-semibold uppercase tracking-[0.06em]">
              Worst calls, all four days
            </h2>
            <Link
              href="/attention" className="flex items-center gap-0.5 text-[11px] text-[var(--ink-3)] hover:text-[var(--ink-1)]"
            >
              by day <ArrowUpRight size={11} />
            </Link>
          </div>

          <ul className="mt-3">
            {data.attention_queue.map((call) => (
              <li key={call.id}>
                <Link
                  href={`/calls/${encodeURIComponent(call.id)}`}
                  className="flex items-start gap-3 border-b border-[var(--hairline)] py-2.5 transition-colors last:border-b-0 hover:bg-[var(--rail)]"
                >
                  <span
                    className={cn(
                      "mt-0.5 shrink-0 rounded border px-1.5 py-0.5 font-mono text-[12px] font-semibold tabular-nums",
                      attentionTone(call.attention_score),
                    )}
                  >
                    {call.attention_score ?? "—"}
                  </span>
                  <span className="min-w-0 flex-1">
                    <span className="block truncate text-[13px] font-medium">
                      {humanLabel(call.intent_label)}
                    </span>
                    <span className="mt-0.5 block truncate text-[12px] text-[var(--ink-3)]">
                      {call.summary ?? "—"}
                    </span>
                    {/* The evidence, inline. Without this the row states a
                        judgment and asks the reader to trust it — the exact
                        thing the system is built not to do. */}
                    {call.intent_evidence && (
                      <span className="mt-1 flex min-w-0 items-baseline gap-1.5 text-[11px]">
                        <span
                          className={cn(
                            "shrink-0 font-mono tabular-nums",
                            call.intent_evidence.verified
                              ? "text-[var(--good)]"
                              : " text-[var(--critical)]",
                          )}
                        >
                          {call.intent_evidence.verified ? "✓" : "⚠"}{" "}
                          {call.intent_evidence.timestamp}
                        </span>
                        {/* min-w-0 as well as truncate: a flex item's min-width
                            is `auto`, so without it the quote refuses to shrink
                            and gets clipped by the parent instead of ellipsised. */}
                        <span className="min-w-0 truncate italic text-[var(--ink-2)]">
                          &ldquo;{call.intent_evidence.quote}&rdquo;
                        </span>
                      </span>
                    )}
                  </span>
                  <span className="shrink-0 pt-0.5 text-right font-mono text-[11px] tabular-nums text-[var(--ink-3)]">
                    <span className="block">{formatDate(call.started_at)}</span>
                    <span className="block">
                      {formatSeconds(call.duration_seconds)} ·{" "}
                      {call.resolution_status ?? "?"}
                    </span>
                  </span>
                </Link>
              </li>
            ))}
          </ul>
        </section>

        <aside className="space-y-4">
          {data.failing_issues.length > 0 && (
            <Exception
              icon={<AlertTriangle size={12} />}
              title={`${data.failing_issues.length} issues failing`}
              href="/trends"
            >
              {data.failing_issues.map((i) => (
                <Row
                  key={i.cluster_id}
                  href={`/trends/${i.cluster_id}`}
                  left={i.label}
                  right={`${(i.resolution_rate * 100).toFixed(0)}% · ${(i.gap * 100).toFixed(0)}pp`}
                />
              ))}
            </Exception>
          )}

          {data.agent_gaps.length > 0 && (
            <Exception
              icon={<GraduationCap size={12} />}
              title={`${data.agent_gaps.length} coaching gaps`}
              href="/agents"
            >
              {data.agent_gaps.map((a) => (
                <Row
                  key={a.agent_id}
                  href={`/agents/${encodeURIComponent(a.agent_id)}`}
                  left={`${a.agent_name} — ${a.issue_label}`}
                  right={`${(a.issue_rate * 100).toFixed(0)}% · ${(a.gap * 100).toFixed(0)}pp`}
                />
              ))}
            </Exception>
          )}

          {data.repeat_contacts.length > 0 && (
            <Exception
              icon={<PhoneCall size={12} />}
              title="Stuck on one issue" href="/repeat-contacts"
            >
              {data.repeat_contacts.map((r) => (
                <Row
                  key={`${r.customer_id}-${r.cluster_id}`}
                  href={`/customers/${encodeURIComponent(r.customer_id)}`}
                  left={`${r.customer_name} — ${r.issue_label}`}
                  right={`${r.call_count}×`}
                />
              ))}
            </Exception>
          )}
        </aside>
      </div>

      {/* ---- full issue breakdown ---------------------------------------- */}
      <section className="border-t border-[var(--hairline)] pt-6">
        <div className="flex items-baseline justify-between">
          <h2 className="text-[12px] font-semibold uppercase tracking-[0.06em]">
            What people call about
          </h2>
          <span className="font-mono text-[11px] tabular-nums text-[var(--ink-3)]">
            {data.issues.reduce((n, i) => n + i.call_count, 0).toLocaleString()} of{" "}
            {k.calls_analysed.toLocaleString()} grouped
          </span>
        </div>
        <div className="mt-4 max-w-3xl">
          <IssueBars issues={data.issues} baseline={data.baseline_resolution} />
        </div>
      </section>

      {/* ---- footer: the corpus, stated plainly -------------------------- */}
      <footer className="flex flex-wrap gap-x-6 gap-y-1 border-t border-[var(--hairline)] pt-4 font-mono text-[11px] tabular-nums text-[var(--ink-3)]">
        {data.days.map((d) => (
          <span key={d.date}>
            {formatDate(d.date)} · {d.call_count} calls · {d.unresolved} unresolved
          </span>
        ))}
      </footer>
    </div>
  );
}
