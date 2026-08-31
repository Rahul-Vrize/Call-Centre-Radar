import type {
  AgentIssueStat,
  Overview,
  AgentStats,
  RepeatContact,
  CallDetail,
  CallSummary,
  Customer,
  AttentionResponse,
  ReviewState,
  TrendsResponse,
} from "./types";

// On the server we hit FastAPI directly — a server component going back out
// through Next's own rewrite would be a pointless extra hop. In the browser we
// use the relative /api path, which next.config.ts rewrites to the backend, so
// there is no CORS surface at all.
function apiBase(): string {
  if (typeof window === "undefined") {
    return process.env.BACKEND_URL ?? "http://localhost:8000";
  }
  return "/api";
}

export type ApiResult<T> =
  | { data: T; error: null }
  | { data: null; error: string };

/**
 * Never throws. A page whose data is missing should say so and still render;
 * a dashboard that white-screens because one endpoint is down is harder to
 * diagnose on stage than one showing an honest error band.
 */
export async function apiGet<T>(
  path: string,
  init?: RequestInit,
): Promise<ApiResult<T>> {
  try {
    const res = await fetch(`${apiBase()}${path}`, {
      // The analysis is precomputed and immutable between pipeline runs, but
      // during the build week we always want what's actually in SQLite.
      cache: "no-store",
      ...init,
    });

    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      return {
        data: null,
        error:
          res.status === 501
            ? `Not implemented yet on the backend (${path})`
            : `${res.status} ${res.statusText} — ${detail.slice(0, 200)}`,
      };
    }

    return { data: (await res.json()) as T, error: null };
  } catch (e) {
    return {
      data: null,
      error: `Could not reach the API at ${apiBase()}${path} — ${
        e instanceof Error ? e.message : String(e)
      }`,
    };
  }
}

export const getOverview = () => apiGet<Overview>("/overview");

export const getCustomers = () => apiGet<Customer[]>("/customers");

export const getCustomerCalls = (customerId: string) =>
  apiGet<CallSummary[]>(`/customers/${encodeURIComponent(customerId)}/calls`);

export const getCall = (callId: string) =>
  apiGet<CallDetail>(`/calls/${encodeURIComponent(callId)}`);

export const getAttention = (date?: string, includeReviewed = false) => {
  const q = new URLSearchParams();
  if (date) q.set("date", date);
  if (includeReviewed) q.set("include_reviewed", "true");
  const qs = q.toString();
  return apiGet<AttentionResponse>(`/attention${qs ? `?${qs}` : ""}`);
};

export const getTrends = () => apiGet<TrendsResponse>("/trends");

export const getClusterCalls = (clusterId: number) =>
  apiGet<CallSummary[]>(`/trends/${clusterId}/calls`);

export const getAgents = () => apiGet<AgentStats[]>("/agents");

export const getAgentIssues = (agentId: string) =>
  apiGet<AgentIssueStat[]>(`/agents/${encodeURIComponent(agentId)}/issues`);

export const getAgentCalls = (agentId: string, clusterId?: number) =>
  apiGet<CallSummary[]>(
    `/agents/${encodeURIComponent(agentId)}/calls` +
      (clusterId != null ? `?cluster_id=${clusterId}` : ""),
  );

export const getRepeatContacts = () =>
  apiGet<RepeatContact[]>("/repeat-contacts");

/**
 * Append one triage event to a call's review log.
 *
 * Browser-only by design: this is the one write in the app, and it is always a
 * user action, so it goes through the /api rewrite like any other client fetch.
 * "Undo" is `action: "reopened"` — a new event, never a deletion, so the record
 * of who closed the call and why survives being reversed.
 */
export async function postReview(
  callId: string,
  body: { action: "reviewed" | "reopened"; reviewer: string; note?: string },
): Promise<ApiResult<ReviewState>> {
  try {
    const res = await fetch(
      `${apiBase()}/calls/${encodeURIComponent(callId)}/review`,
      {
        method: "POST",
        headers: { "content-type": "application/json" },
        body: JSON.stringify({ note: "", ...body }),
        cache: "no-store",
      },
    );
    if (!res.ok) {
      const detail = await res.text().catch(() => "");
      // FastAPI puts the human-readable reason in `detail`; surfacing the raw
      // JSON envelope instead would show the user a stack of braces.
      let message = `${res.status} ${res.statusText}`;
      try {
        const parsed = JSON.parse(detail);
        if (typeof parsed?.detail === "string") message = parsed.detail;
      } catch {
        if (detail) message = detail.slice(0, 200);
      }
      return { data: null, error: message };
    }
    return { data: (await res.json()) as ReviewState, error: null };
  } catch (e) {
    return {
      data: null,
      error: e instanceof Error ? e.message : String(e),
    };
  }
}
