// Mirrors backend/app/schemas/call.py. Keep the two in sync — if a field moves
// there, it moves here.

export interface Evidence {
  turn_id: number;
  timestamp: string; // "HH:MM:SS"
  quote: string;
  verified: boolean; // result of the fuzzy-match check against the transcript
}

export interface Word {
  text: string;
  start: number;
  end: number;
  confidence: number;
}

export interface Turn {
  id: number;
  turn_index: number;
  speaker: "agent" | "customer";
  start_seconds: number;
  end_seconds: number;
  text: string;
  words: Word[];
  mood_score: number | null;
  overlapping: boolean;
}

export interface AttentionFactor {
  factor: string;
  weight: number;
  evidence: Evidence | null;
}

export interface CallDetail {
  id: string;
  customer_id: string;
  customer_name: string;
  agent_id: string;
  agent_name: string;
  started_at: string;
  duration_seconds: number;
  audio_url: string;
  transcript_provider: "assemblyai" | "whisper";

  turns: Turn[];

  intent_label: string | null;
  intent_evidence: Evidence | null;

  resolution_status: "resolved" | "unresolved" | "partial" | null;
  resolution_evidence: Evidence | null;

  summary: string | null; // <= 40 words

  mood_shift_turn_id: number | null;
  mood_shift_evidence: Evidence | null;

  attention_score: number | null; // 0-100
  attention_factors: AttentionFactor[];
}

export interface CallSummary {
  id: string;
  started_at: string;
  duration_seconds: number;
  intent_label: string | null;
  resolution_status: string | null;
  summary: string | null;
  attention_score: number | null;
}

export interface Customer {
  id: string;
  name: string;
  call_count: number;
  last_contact: string | null;
}

export interface AgentStats {
  id: string;
  name: string;
  call_count: number;
  avg_handle_time_seconds: number;
  resolution_rate: number;
  avg_attention_score: number;
}

export interface TrendingIssue {
  cluster_id: number;
  label: string;
  call_count: number;
  counts_by_day: Record<string, number>;

  // Outcome quality — the signal that actually separates one issue from
  // another here. Per-day counts mirror the recording schedule, not a trend.
  resolution_rate: number;
  avg_attention_score: number;
  avg_handle_time_seconds: number;

  /** Share of each day's calls, so days of very different size compare. */
  share_by_day: Record<string, number>;
}

export interface TrendsBaseline {
  call_count: number;
  resolution_rate: number;
  avg_attention_score: number;
  avg_handle_time_seconds: number;
}

export interface TrendsResponse {
  baseline: TrendsBaseline;
  issues: TrendingIssue[];
}

export interface AttentionDay {
  date: string;
  call_count: number;
}

export interface AttentionResponse {
  /** The day shown. Not "today" — the corpus is four days in 2020. */
  date: string | null;
  available_dates: AttentionDay[];
  calls: CallSummary[];
}
