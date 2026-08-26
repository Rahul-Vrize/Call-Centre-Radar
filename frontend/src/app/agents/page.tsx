// Per-agent volume, handle time and outcomes — GET /agents.
import { getAgents } from "@/lib/api";
import { formatSeconds } from "@/lib/utils";
import ApiNotice from "@/components/ApiNotice";

export default async function AgentsDashboard() {
  const { data: agents, error } = await getAgents();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Agents</h1>
        <p className="mt-1 text-sm text-neutral-500">
          Volume, handle time and outcomes — plain rollups over the stored
          analysis.
        </p>
      </div>

      {error && <ApiNotice error={error} />}

      {agents && agents.length > 0 && (
        <div className="overflow-hidden rounded-lg border border-neutral-200 dark:border-neutral-800">
          <table className="w-full text-sm">
            <thead className="border-b border-neutral-200 bg-neutral-50 text-left text-xs uppercase tracking-wide text-neutral-500 dark:border-neutral-800 dark:bg-neutral-900">
              <tr>
                <th className="px-4 py-2.5 font-medium">Agent</th>
                <th className="px-4 py-2.5 font-medium">Calls</th>
                <th className="px-4 py-2.5 font-medium">Avg handle time</th>
                <th className="px-4 py-2.5 font-medium">Resolution rate</th>
                <th className="px-4 py-2.5 font-medium">Avg attention</th>
              </tr>
            </thead>
            <tbody>
              {agents.map((a) => (
                <tr
                  key={a.id}
                  className="border-b border-neutral-100 last:border-b-0 dark:border-neutral-900"
                >
                  <td className="px-4 py-2.5 font-medium">{a.name}</td>
                  <td className="px-4 py-2.5 tabular-nums">{a.call_count}</td>
                  <td className="px-4 py-2.5 tabular-nums">
                    {formatSeconds(a.avg_handle_time_seconds)}
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">
                    {(a.resolution_rate * 100).toFixed(0)}%
                  </td>
                  <td className="px-4 py-2.5 tabular-nums">
                    {a.avg_attention_score.toFixed(0)}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
