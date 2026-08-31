"use client";

import { useEffect, useRef, useState } from "react";
import { Pause, Play } from "lucide-react";
import { usePlayer } from "./PlayerContext";
import { formatSeconds } from "@/lib/utils";

interface Props {
  audioUrl: string;
}

/** Wavesurfer paints to a canvas, so it cannot take a CSS variable — it needs a
 *  resolved colour. Reading the token off the document keeps the waveform on the
 *  same palette as everything around it (and in the right theme) instead of the
 *  hardcoded slate/indigo/rose that made this card the one element on the page
 *  wearing colours from nowhere. */
function token(name: string, fallback: string): string {
  if (typeof window === "undefined") return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name);
  return v.trim() || fallback;
}

export default function WaveformPlayer({ audioUrl }: Props) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { register, setCurrentTime } = usePlayer();
  const [playing, setPlaying] = useState(false);
  const [duration, setDuration] = useState(0);
  const [time, setTime] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const wsRef = useRef<import("wavesurfer.js").default | null>(null);

  useEffect(() => {
    if (!containerRef.current || !audioUrl) return;

    let disposed = false;
    let ws: import("wavesurfer.js").default | null = null;

    // Imported here rather than at module scope: wavesurfer touches browser
    // globals, and this file is still server-rendered even as a client
    // component.
    void (async () => {
      const { default: WaveSurfer } = await import("wavesurfer.js");
      if (disposed || !containerRef.current) return;

      ws = WaveSurfer.create({
        container: containerRef.current,
        height: 72,
        waveColor: token("--ink-3", "#898781"),
        progressColor: token("--bar", "#2a78d6"),
        cursorColor: token("--critical", "#d03b3b"),
        barWidth: 2,
        barGap: 1,
        barRadius: 2,
        // Streams via a real <audio> element, so the browser issues HTTP Range
        // requests instead of downloading the whole mp3 before you can scrub.
        backend: "MediaElement",
        url: audioUrl,
      });

      wsRef.current = ws;
      register({ seek: (seconds: number) => ws?.setTime(seconds) });

      ws.on("ready", () => setDuration(ws?.getDuration() ?? 0));
      ws.on("play", () => setPlaying(true));
      ws.on("pause", () => setPlaying(false));
      ws.on("finish", () => setPlaying(false));
      ws.on("timeupdate", (t: number) => {
        setTime(t);
        setCurrentTime(t);
      });
      ws.on("error", (e: Error) => setError(e?.message ?? " audio failed to load"));
    })();

    return () => {
      disposed = true;
      register(null);
      wsRef.current = null;
      ws?.destroy();
    };
  }, [audioUrl, register, setCurrentTime]);

  if (!audioUrl) {
    return (
      <div className="rounded-lg border border-dashed border-[var(--hairline)] p-6 text-sm text-[var(--ink-3)]">
        No recording linked to this call.
      </div>
    );
  }

  return (
    <div className="min-w-0 rounded-lg border border-[var(--hairline)] p-4">
      <div className="flex items-center gap-4">
        <button
          type="button" onClick={() => wsRef.current?.playPause()}
          aria-label={playing ? "Pause" : " Play"}
          className="flex size-10 shrink-0 items-center justify-center rounded-full bg-[var(--bar)] text-white transition hover:brightness-110"
        >
          {playing ? <Pause size={18} /> : <Play size={18} className="ml-0.5" />}
        </button>
        <div ref={containerRef} className="min-w-0 flex-1" />
        <span className="shrink-0 font-mono text-xs tabular-nums text-[var(--ink-3)]">
          {formatSeconds(time)} / {formatSeconds(duration)}
        </span>
      </div>
      {error && (
        <p className="mt-2 text-xs text-[var(--critical)]">
          Audio error: {error}
        </p>
      )}
    </div>
  );
}
