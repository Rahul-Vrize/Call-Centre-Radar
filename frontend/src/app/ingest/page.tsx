// The live pipeline — POST /ingest.
//
// Deliberately the same code path the overnight batch uses. If a recording the
// system has never seen comes back with verified citations, the precomputed
// 1,441 calls are demonstrably not a lookup table.
import IngestForm from "@/components/IngestForm";

export const metadata = {
  title: "Analyse a new call · Call-Centre Radar",
};

export default function IngestPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Analyse a new call</h1>
        <p className="mt-1 text-sm text-[var(--ink-3)]">
          Upload a recording the system has never seen. It runs the same
          pipeline as the other 1,441 calls — channel split, transcription, mood
          scoring, change-point detection, grounded reasoning, and citation
          verification — then opens the analysed call.
        </p>
      </div>

      <IngestForm />

      <div className="rounded-lg border border-[var(--hairline)] p-4 text-sm text-[var(--ink-3)]">
        <p className="font-medium text-[var(--ink-1)]">
          What happens to the recording
        </p>
        <p className="mt-1">
          It is stored alongside the corpus so the call is playable afterwards,
          and the customer appears in the customer list with their new call. The
          audio must be stereo — this system relies on channel separation
          (left&nbsp;=&nbsp;agent, right&nbsp;=&nbsp;customer) rather than
          diarization, so a mono file is rejected rather than mis-attributed.
        </p>
      </div>
    </div>
  );
}
