// One agent's full per-issue breakdown — the coaching detail view.
import Link from "next/link";
import { getAgentIssues, getAgents } from "@/lib/api";
import { cn } from "@/lib/utils";
import ApiNotice from "@/components/ApiNotice";

export default async function AgentDetail({
  params,
}: {
  params: Promise<{ agentId: string }>;
}) {
  const { agentId } = await params;
  const [{ data: issues, error }, { data: agents }] = await Promise.all([
    getAgentIssues(agentId),
    getAgents(),
  ]);
  const agent = agents?.find((a) => a.id === agentId);

  return (
    <div className="space-y-6">
      <div>
        <Link
          href="/agents"
          className="text-sm text-[var(--bar)] hover:underline"
        >
          ← All agents
        </Link>
        <h1 className="mt-1 text-2xl font-semibold">{agent?.name ?? agentId}</h1>
        {agent && (
          <p className="mt-1 font-mono text-sm text-[var(--ink-3)]">
            {agent.call_count} calls ·{" "}
            {(agent.resolution_rate * 100).toFixed(1)}% resolved overall ·
            attention {agent.avg_attention_score.toFixed(1)}
          </p>
        )}
      </div>

      {error && <ApiNotice error={error} />}

      {issues && issues.length > 0 && agent && (
        <>
          <p className="text-sm text-[var(--ink-3)]">
            Each bar is this agent&apos;s resolution rate on one issue, against
            their own {(agent.resolution_rate * 100).toFixed(0)}% overall
            baseline (the dashed line).
          </p>

          <ul className="space-y-3">
            {issues.map((issue) => {
              const gap = issue.delta_vs_self;
              const weak = gap < -0.1;
              return (
                <li
                  key={issue.cluster_id}
                  className={cn(
                    "rounded-lg border p-4",
                    weak
                      ? "border-[var(--critical)]/40 bg-[var(--critical)]/5"
                      : "border-[var(--hairline)] ",
                  )}
                >
                  <div className="flex items-baseline justify-between gap-4">
                    <Link
                      href={`/trends/${issue.cluster_id}`}
                      className="font-medium hover:underline"
                    >
                      {issue.label}
                    </Link>
                    <span className="shrink-0 font-mono text-sm tabular-nums">
                      {(issue.resolution_rate * 100).toFixed(0)}%
                      <span
                        className={cn(
                          "ml-2 text-xs",
                          weak
                            ? "text-[var(--critical)] "
                            : "text-[var(--ink-3)]",
                        )}
                      >
                        {gap >= 0 ? "+" : ""}
                        {(gap * 100).toFixed(0)}pp
                      </span>
                    </span>
                  </div>

                  {/* Bar with the agent's own baseline marked, so the gap is
                      visible without doing arithmetic. */}
                  <div className="relative mt-3 h-2 w-full rounded-full bg-[var(--rail)]">
                    <div
                      style={{ width: `${issue.resolution_rate * 100}%` }}
                      className={cn(
                        "h-full rounded-full",
                        weak ? "bg-[var(--critical)]" : "bg-[var(--bar)]",
                      )}
                    />
                    <div
                      style={{ left: `${agent.resolution_rate * 100}%` }}
                      title={`this agent's overall rate: ${(agent.resolution_rate * 100).toFixed(0)}%`}
                      className="absolute -top-1 h-4 border-l-2 border-dashed border-[var(--ink-3)]"
                    />
                  </div>

                  <p className="mt-2 font-mono text-xs text-[var(--ink-3)]">
                    {issue.call_count} calls
                  </p>
                </li>
              );
            })}
          </ul>
        </>
      )}

      {issues && issues.length === 0 && (
        <p className="text-sm text-[var(--ink-3)]">
          No issue has at least 8 calls for this agent — not enough data to
          judge per-issue performance.
        </p>
      )}
    </div>
  );
}
