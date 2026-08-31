"use client";

import { useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Loader2, Radar, Upload } from "lucide-react";
import { cn } from "@/lib/utils";
import type { CallDetail } from "@/lib/types";

/** What the pipeline is doing, roughly, while the request is in flight.
 *  The API is a single synchronous call, so these are time-based rather than
 *  real progress events — labelled as an estimate rather than pretending to
 *  be telemetry we don't have. */
const STAGES = [
  "Splitting channels…",
  "Transcribing both speakers…",
  "Merging turns…",
  "Scoring mood, detecting the shift…",
  "Extracting intent and resolution…",
  "Verifying citations…",
];

export default function IngestForm() {
  const router = useRouter();
  const inputRef = useRef<HTMLInputElement>(null);

  const [file, setFile] = useState<File | null>(null);
  const [customer, setCustomer] = useState("");
  const [agent, setAgent] = useState("");
  const [busy, setBusy] = useState(false);
  const [stage, setStage] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [dragging, setDragging] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    if (!file || busy) return;

    setBusy(true);
    setError(null);
    setStage(0);
    const ticker = setInterval(
      () => setStage((s) => Math.min(s + 1, STAGES.length - 1)),
      2200,
    );

    try {
      const body = new FormData();
      body.append("audio", file);
      body.append("customer_name", customer.trim() || "Unknown caller");
      body.append("agent_name", agent.trim() || "Unknown agent");

      const res = await fetch("/api/ingest", { method: "POST", body });
      const payload = await res.json();

      if (!res.ok) {
        throw new Error(
          typeof payload?.detail === "string"
            ? payload.detail
            : `Ingestion failed (${res.status})`,
        );
      }

      // Straight to the analysed call — the point of the demo is that the
      // dashboard treats a brand-new recording exactly like the other 1,441.
      router.push(`/calls/${encodeURIComponent((payload as CallDetail).id)}`);
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
      setBusy(false);
    } finally {
      clearInterval(ticker);
    }
  }

  return (
    <form onSubmit={submit} className="space-y-5">
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        onDragOver={(e) => {
          e.preventDefault();
          setDragging(true);
        }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setDragging(false);
          const dropped = e.dataTransfer.files?.[0];
          if (dropped) setFile(dropped);
        }}
        className={cn(
          "flex w-full flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed px-6 py-10 transition",
          dragging
            ? "border-[var(--bar)] bg-[var(--bar)]/5"
            : "border-[var(--hairline)] hover:border-[var(--bar)]",
        )}
      >
        <Upload size={22} className="text-[var(--ink-3)]" />
        {file ? (
          <>
            <span className="font-medium">{file.name}</span>
            <span className="font-mono text-xs text-[var(--ink-3)]">
              {(file.size / 1024 / 1024).toFixed(1)} MB
            </span>
          </>
        ) : (
          <>
            <span className="text-sm font-medium">
              Drop a recording here, or click to choose
            </span>
            <span className="text-xs text-[var(--ink-3)]">
              Stereo audio — left channel agent, right channel customer
            </span>
          </>
        )}
      </button>

      <input
        ref={inputRef}
        type="file"
        accept="audio/*,.mp3,.wav"
        className="hidden"
        onChange={(e) => setFile(e.target.files?.[0] ?? null)}
      />

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-xs uppercase tracking-wide text-[var(--ink-3)]">
            Customer name
          </span>
          <input
            value={customer}
            onChange={(e) => setCustomer(e.target.value)}
            placeholder="Mary Smith"
            className="mt-1 w-full rounded-md border border-[var(--hairline)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--bar)]"
          />
        </label>
        <label className="block">
          <span className="text-xs uppercase tracking-wide text-[var(--ink-3)]">
            Agent name
          </span>
          <input
            value={agent}
            onChange={(e) => setAgent(e.target.value)}
            placeholder="Robert"
            className="mt-1 w-full rounded-md border border-[var(--hairline)] bg-transparent px-3 py-2 text-sm outline-none focus:border-[var(--bar)]"
          />
        </label>
      </div>

      <button
        type="submit"
        disabled={!file || busy}
        className="flex w-full items-center justify-center gap-2 rounded-md bg-[var(--bar)] px-4 py-2.5 text-sm font-medium text-white transition hover:brightness-110 disabled:cursor-not-allowed disabled:opacity-40"
      >
        {busy ? <Loader2 size={16} className="animate-spin" /> : <Radar size={16} />}
        {busy ? "Analysing…" : "Run the pipeline"}
      </button>

      {busy && (
        <div className="rounded-lg border border-[var(--hairline)] p-4">
          <p className="flex items-center gap-2 text-sm">
            <Loader2 size={14} className="animate-spin text-[var(--bar)]" />
            {STAGES[stage]}
          </p>
          <div className="mt-3 h-1 w-full overflow-hidden rounded-full bg-[var(--rail)]">
            <div
              style={{ width: `${((stage + 1) / STAGES.length) * 100}%` }}
              className="h-full rounded-full bg-[var(--bar)] transition-all duration-700"
            />
          </div>
          <p className="mt-2 text-xs text-[var(--ink-3)]">
            Estimated stage — the API runs this as one synchronous call, so this
            is elapsed time rather than live progress.
          </p>
        </div>
      )}

      {error && (
        <div className="rounded-lg border border-[var(--critical)]/40 bg-[var(--critical)]/5 p-4 text-sm">
          <p className="font-medium text-[var(--critical)]">
            Ingestion failed
          </p>
          <p className="mt-1 text-[var(--ink-2)]">{error}</p>
        </div>
      )}
    </form>
  );
}
