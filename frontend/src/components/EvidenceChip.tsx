// The rubric, made interactive: click a claim's chip to seek the audio to
// its cited timestamp and highlight the quoted words in the transcript.
interface Props {
  timestamp: string;
  quote: string;
  verified: boolean;
  onClick: () => void;
}

export default function EvidenceChip({ timestamp, quote, verified, onClick }: Props) {
  return (
    <button
      onClick={onClick}
      title={quote}
      className={`text-xs font-mono px-2 py-0.5 rounded border ${
        verified ? "border-amber-500 text-amber-700" : "border-red-500 text-red-700"
      }`}
    >
      {verified ? "◐" : "⚠"} {timestamp}
    </button>
  );
}
