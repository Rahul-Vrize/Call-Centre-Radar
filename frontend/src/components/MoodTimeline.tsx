// The mood-score-over-time chart (Recharts), with the change-point-detected
// shift marked and clickable to reveal its evidence quote.
interface Turn {
  id: number;
  start_seconds: number;
  mood_score: number | null;
}

interface Props {
  turns: Turn[];
  shiftTurnId: number | null;
}

export default function MoodTimeline({ turns, shiftTurnId }: Props) {
  return (
    <div className="p-4 border rounded">
      TODO: mood timeline chart {shiftTurnId !== null && `(shift at turn ${shiftTurnId})`}
    </div>
  );
}
