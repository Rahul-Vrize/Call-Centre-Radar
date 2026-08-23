// The core per-call view: playable recording, transcript, mood timeline,
// intent/resolution/summary, attention score — every judgment carrying a
// clickable evidence chip that seeks the audio and highlights the quote.
// GET /calls/:callId
import WaveformPlayer from "../components/WaveformPlayer";
import TranscriptPanel from "../components/TranscriptPanel";
import MoodTimeline from "../components/MoodTimeline";
import AttentionBadge from "../components/AttentionBadge";

export default function CallDetail() {
  return (
    <div className="p-4 space-y-4">
      <WaveformPlayer audioUrl="" />
      <MoodTimeline turns={[]} shiftTurnId={null} />
      <TranscriptPanel turns={[]} onSeek={() => {}} />
      <AttentionBadge score={null} factors={[]} />
    </div>
  );
}
