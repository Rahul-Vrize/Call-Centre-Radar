"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { Check, RotateCcw } from "lucide-react";
import type { ReviewState } from "@/lib/types";
import { postReview } from "@/lib/api";
import { cn, formatDateTime } from "@/lib/utils";

const REVIEWER_KEY = "radar.reviewer";

/**
 * Manager triage — the one place a human writes to this system.
 *
 * Everything else here is the model making a claim and citing the second it
 * came from. This applies the same rule to people: closing a call is not a flag
 * being flipped, it is an event with an author, a time and a reason, and it
 * stays on the record after it is undone. "Reopen" appends; it never erases.
 *
 * The reviewer name is a free-text field remembered in this browser, and it is
 * labelled as such. There is no auth in this app, so a name here is a claim
 * about who acted — inventing a permissions UI on top of no permissions would
 * be exactly the kind of unearned assertion the rest of the design refuses.
 */
export default function ReviewPanel({
  callId,
  initial,
}: {
  callId: string;
  initial: ReviewState;
}) {
  const router = useRouter();
  const [state, setState] = useState(initial);
  // Uncontrolled: the remembered name arrives after mount, and seeding it into
  // React state from an effect both trips react-hooks/set-state-in-effect and
  // risks a hydration mismatch (server renders empty, client renders a name).
  // Writing straight to the DOM node sidesteps both.
  const reviewerRef = useRef<HTMLInputElement>(null);
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [showHistory, setShowHistory] = useState(false);

  // Remembered per browser so a manager working a queue types their name once.
  // Wrapped because storage throws outright in some contexts (private windows,
  // blocked site data) rather than merely returning null.
  useEffect(() => {
    try {
      const saved = localStorage.getItem(REVIEWER_KEY);
      if (saved && reviewerRef.current && !reviewerRef.current.value) {
        reviewerRef.current.value = saved;
      }
    } catch {
      /* no stored name — the field just starts empty */
    }
  }, []);

  async function submit(action: "reviewed" | "reopened") {
    const who = (reviewerRef.current?.value ?? "").trim();
    if (!who) {
      setError("Add your name first — an unattributed review isn't a record.");
      return;
    }
    setBusy(true);
    setError(null);
    try {
      localStorage.setItem(REVIEWER_KEY, who);
    } catch {
      /* not fatal — the name just won't be remembered next time */
    }

    const { data, error: err } = await postReview(callId, {
      action,
      reviewer: who,
      note: note.trim(),
    });
    setBusy(false);

    if (err || !data) {
      setError(err ?? "Could not save.");
      return;
    }
    setState(data);
    setNote("");
    // The queues filter on review state, so they are now stale.
    router.refresh();
  }

  return (
    <div
      className={cn(
        "rounded-lg border p-4",
        state.is_reviewed
          ? "border-[var(--good)]/40 bg-[var(--good)]/5"
          : "border-[var(--hairline)]",
      )}
    >
      <div className="flex items-baseline justify-between gap-3">
        <p className="text-xs font-semibold uppercase tracking-wide text-[var(--ink-3)]">
          Manager review
        </p>
        {state.history.length > 0 && (
          <button
            type="button"
            onClick={() => setShowHistory((v) => !v)}
            aria-expanded={showHistory}
            className="font-mono text-[10px] text-[var(--ink-3)] transition-colors hover:text-[var(--ink-1)]"
          >
            {showHistory ? "hide" : `history (${state.history.length})`}
          </button>
        )}
      </div>

      {/* Current state, when there is one to show. */}
      {state.is_reviewed ? (
        <div className="mt-3 space-y-1.5">
          <p className="flex items-center gap-2 text-sm">
            <Check size={15} className="shrink-0 text-[var(--good)]" />
            <span>
              Reviewed by{" "}
              <span className="font-medium">{state.reviewed_by}</span>
            </span>
          </p>
          <p className="font-mono text-[11px] text-[var(--ink-3)]">
            {state.reviewed_at ? formatDateTime(state.reviewed_at) : ""}
          </p>
          {state.note && (
            <p className="border-l-2 border-[var(--hairline)] pl-2 text-sm text-[var(--ink-2)]">
              {state.note}
            </p>
          )}
        </div>
      ) : (
        <p className="mt-3 text-sm text-[var(--ink-2)]">
          {state.history.length > 0
            ? "Reopened — back in the queue."
            : "Not yet triaged. Marking it reviewed removes it from the queue."}
        </p>
      )}

      {/* The form sits OUTSIDE that branch on purpose. Reopening is an
          attributed act too — it is the reviewer of record for the reversal —
          so the name field has to be reachable in both states. Rendering it
          only in the un-reviewed branch left "Reopen" asking for a name with
          no box to type it in. */}
      <div className="mt-3 space-y-2">
        <label className="block">
          <span className="sr-only">Your name</span>
          <input
            ref={reviewerRef}
            defaultValue=""
            placeholder="Your name"
            maxLength={80}
            className="w-full rounded-md border border-[var(--hairline)] bg-transparent px-3 py-1.5 text-sm outline-none placeholder:text-[var(--ink-3)] focus:border-[var(--bar)]"
          />
        </label>
        <label className="block">
          <span className="sr-only">
            {state.is_reviewed ? "Why you're reopening" : "What you did"}
          </span>
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder={
              state.is_reviewed
                ? "Why you're reopening (optional)"
                : "What you did (optional)"
            }
            maxLength={500}
            className="w-full rounded-md border border-[var(--hairline)] bg-transparent px-3 py-1.5 text-sm outline-none placeholder:text-[var(--ink-3)] focus:border-[var(--bar)]"
          />
        </label>

        {state.is_reviewed ? (
          <>
            <button
              type="button"
              disabled={busy}
              onClick={() => submit("reopened")}
              className="inline-flex items-center gap-1.5 rounded-md border border-[var(--hairline)] px-3 py-1.5 text-sm transition-colors hover:border-[var(--ink-3)] disabled:opacity-50"
            >
              <RotateCcw size={13} />
              {busy ? "Reopening…" : "Reopen"}
            </button>
            <p className="text-[11px] text-[var(--ink-3)]">
              Reopening adds an entry — it does not erase this one.
            </p>
          </>
        ) : (
          <button
            type="button"
            disabled={busy}
            onClick={() => submit("reviewed")}
            className="inline-flex items-center gap-1.5 rounded-md bg-[var(--bar)] px-3 py-1.5 text-sm font-medium text-white transition hover:brightness-110 disabled:opacity-50"
          >
            <Check size={14} />
            {busy ? "Saving…" : "Mark reviewed"}
          </button>
        )}
      </div>

      {error && (
        <p className="mt-2 text-[11px] text-[var(--critical)]">{error}</p>
      )}

      {showHistory && state.history.length > 0 && (
        <ul className="mt-3 space-y-2 border-t border-[var(--hairline)] pt-3">
          {state.history.map((h, i) => (
            <li key={`${h.created_at}-${i}`} className="text-[11px]">
              <span className="flex items-baseline gap-1.5">
                <span
                  className={cn(
                    "font-mono font-semibold",
                    h.action === "reviewed"
                      ? "text-[var(--good)]"
                      : "text-[var(--warning)]",
                  )}
                >
                  {h.action}
                </span>
                <span className="text-[var(--ink-2)]">{h.reviewer}</span>
                <span className="ml-auto shrink-0 font-mono text-[var(--ink-3)]">
                  {formatDateTime(h.created_at)}
                </span>
              </span>
              {h.note && (
                <span className="mt-0.5 block text-[var(--ink-3)]">{h.note}</span>
              )}
            </li>
          ))}
        </ul>
      )}

      <p className="mt-3 border-t border-[var(--hairline)] pt-2 text-[11px] leading-relaxed text-[var(--ink-3)]">
        Separate from the call&apos;s outcome. This records that a person dealt
        with it; whether the call itself resolved stays as the transcript showed
        it, so the resolution rates elsewhere never move because of a click.
      </p>
    </div>
  );
}
