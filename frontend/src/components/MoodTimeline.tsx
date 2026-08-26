"use client";

import {
  CartesianGrid,
  Line,
  LineChart,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { Turn } from "@/lib/types";
import { formatSeconds } from "@/lib/utils";
import { usePlayer } from "./PlayerContext";

interface Props {
  turns: Turn[];
  shiftTurnId: number | null;
}

/**
 * The customer's fused mood score over the call. This is the same series the
 * change-point detector ran on, so the chart and the "why" are one
 * computation — the marked shift is a detected breakpoint, not a drawn guess.
 */
export default function MoodTimeline({ turns, shiftTurnId }: Props) {
  const { seekTo } = usePlayer();

  const points = turns
    .filter((t) => t.speaker === "customer" && t.mood_score !== null)
    .map((t) => ({
      turnId: t.id,
      seconds: t.start_seconds,
      mood: t.mood_score as number,
      text: t.text,
    }));

  if (points.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-neutral-300 p-6 text-sm text-neutral-500 dark:border-neutral-700">
        No mood series yet — the scoring stage of the pipeline hasn&apos;t run
        for this call.
      </div>
    );
  }

  const shiftPoint = points.find((p) => p.turnId === shiftTurnId);

  return (
    <div className="rounded-lg border border-neutral-200 p-4 dark:border-neutral-800">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-neutral-500">
        Customer mood
      </h3>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart
          data={points}
          margin={{ top: 4, right: 8, bottom: 4, left: -24 }}
          onClick={(state) => {
            // recharts 3 hands back the active index, not the payload.
            const i = Number(state?.activeIndex);
            const point = Number.isInteger(i) ? points[i] : undefined;
            if (point) seekTo(point.seconds);
          }}
        >
          <CartesianGrid strokeDasharray="3 3" className="stroke-neutral-200 dark:stroke-neutral-800" />
          <XAxis
            dataKey="seconds"
            type="number"
            domain={["dataMin", "dataMax"]}
            tickFormatter={formatSeconds}
            tick={{ fontSize: 11 }}
            stroke="currentColor"
            className="text-neutral-400"
          />
          <YAxis
            domain={[-1, 1]}
            ticks={[-1, 0, 1]}
            tick={{ fontSize: 11 }}
            stroke="currentColor"
            className="text-neutral-400"
          />
          <Tooltip
            labelFormatter={(v) => formatSeconds(Number(v))}
            formatter={(value) => [Number(value).toFixed(2), "mood"]}
            contentStyle={{ fontSize: 12, borderRadius: 6 }}
          />
          <ReferenceLine y={0} className="stroke-neutral-300 dark:stroke-neutral-700" />
          {shiftPoint && (
            <ReferenceLine
              x={shiftPoint.seconds}
              stroke="#f59e0b"
              strokeWidth={2}
              label={{ value: "shift", fontSize: 10, fill: "#f59e0b", position: "top" }}
            />
          )}
          <Line
            type="monotone"
            dataKey="mood"
            stroke="#6366f1"
            strokeWidth={2}
            dot={{ r: 2 }}
            activeDot={{ r: 5 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-1 text-xs text-neutral-400">
        Click the chart to seek the recording.
      </p>
    </div>
  );
}
