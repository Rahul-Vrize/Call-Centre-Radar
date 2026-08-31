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
      <div className="rounded-lg border border-dashed border-[var(--hairline)] p-6 text-sm text-[var(--ink-3)]">
        No mood series yet — the scoring stage of the pipeline hasn&apos;t run
        for this call.
      </div>
    );
  }

  const shiftPoint = points.find((p) => p.turnId === shiftTurnId);

  return (
    <div className="min-w-0 rounded-lg border border-[var(--hairline)] p-4">
      <h3 className="mb-3 text-xs font-semibold uppercase tracking-wide text-[var(--ink-3)]">
        Customer mood
      </h3>
      <ResponsiveContainer width="100%" height={160}>
        <LineChart
          data={points}
          // Symmetric right/left insets so the first and last x-tick have room
          // to centre under their point instead of being clipped by the card.
          // A negative left margin (the old value) pulled the y-labels under
          // the border and left the plot visibly off-centre in its card.
          margin={{ top: 8, right: 12, bottom: 0, left: 0 }}
          onClick={(state) => {
            // recharts 3 hands back the active index, not the payload.
            const i = Number(state?.activeIndex);
            const point = Number.isInteger(i) ? points[i] : undefined;
            if (point) seekTo(point.seconds);
          }}
        >
          <CartesianGrid
            strokeDasharray="3 3" stroke="var(--hairline)" vertical={false}
          />
          <XAxis
            dataKey="seconds" type="number" domain={["dataMin", "dataMax"]}
            tickFormatter={formatSeconds}
            tick={{ fontSize: 11, fill: "var(--ink-3)" }}
            // Recharts keeps every tick it can fit, which crowds the last two
            // together on a short call. Fixed interior ticks plus padded ends
            // give an evenly spaced axis at any duration.
            tickCount={5}
            minTickGap={28}
            tickMargin={8}
            axisLine={{ stroke: "var(--hairline)" }}
            tickLine={false}
          />
          <YAxis
            domain={[-1, 1]}
            ticks={[-1, 0, 1]}
            width={28}
            tick={{ fontSize: 11, fill: "var(--ink-3)" }}
            tickMargin={4}
            axisLine={false}
            tickLine={false}
          />
          <Tooltip
            labelFormatter={(v) => formatSeconds(Number(v))}
            formatter={(value) => [Number(value).toFixed(2), "mood"]}
            cursor={{ stroke: "var(--ink-3)", strokeDasharray: "3 3" }}
            contentStyle={{
              fontSize: 12,
              borderRadius: 6,
              background: "var(--surface-2)",
              border: "1px solid var(--hairline)",
              color: "var(--ink-1)",
            }}
            labelStyle={{ color: "var(--ink-2)" }}
          />
          <ReferenceLine y={0} stroke="var(--hairline)" />
          {shiftPoint && (
            <ReferenceLine
              x={shiftPoint.seconds}
              stroke="var(--warning)" strokeWidth={2}
              label={{
                value: "shift",
                fontSize: 10,
                fill: "var(--warning)",
                position: "top",
              }}
            />
          )}
          <Line
            type="monotone" dataKey="mood" stroke="var(--bar)" strokeWidth={2}
            dot={{ r: 2, fill: "var(--bar)", strokeWidth: 0 }}
            activeDot={{ r: 5, stroke: "var(--surface-1)", strokeWidth: 2 }}
            isAnimationActive={false}
          />
        </LineChart>
      </ResponsiveContainer>
      <p className="mt-1 text-xs text-[var(--ink-3)]">
        Click the chart to seek the recording.
      </p>
    </div>
  );
}
