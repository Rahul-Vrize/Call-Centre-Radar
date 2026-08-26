import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

/** Seconds -> "MM:SS" (or "H:MM:SS" past an hour). Matches the transcript's
 *  evidence timestamps so a chip and a turn read the same way. */
export function formatSeconds(seconds: number): string {
  if (!Number.isFinite(seconds) || seconds < 0) return "00:00";
  const s = Math.floor(seconds % 60);
  const m = Math.floor((seconds / 60) % 60);
  const h = Math.floor(seconds / 3600);
  const mm = String(m).padStart(2, "0");
  const ss = String(s).padStart(2, "0");
  return h > 0 ? `${h}:${mm}:${ss}` : `${mm}:${ss}`;
}

/** "HH:MM:SS" or "MM:SS" -> seconds, for seeking from an evidence chip. */
export function parseTimestamp(timestamp: string): number {
  const parts = timestamp.split(":").map(Number);
  if (parts.some((n) => !Number.isFinite(n))) return 0;
  return parts.reduce((acc, part) => acc * 60 + part, 0);
}

export function formatDateTime(iso: string): string {
  const d = new Date(iso);
  return Number.isNaN(d.getTime()) ? iso : d.toLocaleString();
}

/** Shared colour ramp for the 0-100 needs-attention score. */
export function attentionTone(score: number | null): string {
  if (score === null) return "border-neutral-300 text-neutral-500 dark:border-neutral-700 dark:text-neutral-400";
  if (score >= 75) return "border-red-500/60 text-red-600 bg-red-500/10 dark:text-red-400";
  if (score >= 50) return "border-amber-500/60 text-amber-600 bg-amber-500/10 dark:text-amber-400";
  return "border-emerald-500/60 text-emerald-600 bg-emerald-500/10 dark:text-emerald-400";
}
