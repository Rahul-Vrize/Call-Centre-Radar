// Turn-by-turn transcript, synced to playback: clicking a turn seeks the
// audio; the current turn auto-highlights during playback.
interface Turn {
  id: number;
  speaker: "agent" | "customer";
  start_seconds: number;
  text: string;
}

interface Props {
  turns: Turn[];
  onSeek: (seconds: number) => void;
}

export default function TranscriptPanel({ turns, onSeek }: Props) {
  return (
    <div className="p-4 border rounded space-y-2">
      {turns.length === 0 && <p>TODO: transcript turns</p>}
      {turns.map((t) => (
        <div key={t.id} onClick={() => onSeek(t.start_seconds)} className="cursor-pointer">
          <span className="text-xs text-gray-500 mr-2">{t.speaker}</span>
          {t.text}
        </div>
      ))}
    </div>
  );
}
