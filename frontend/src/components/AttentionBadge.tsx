// The 0-100 needs-attention score with its contributing factors on hover,
// each factor optionally carrying its own EvidenceChip.
interface Factor {
  factor: string;
  weight: number;
}

interface Props {
  score: number | null;
  factors: Factor[];
}

export default function AttentionBadge({ score, factors }: Props) {
  return (
    <div className="p-4 border rounded">
      <span className="font-mono">attention {score ?? "—"}</span>
      <ul className="text-sm text-gray-600">
        {factors.map((f) => (
          <li key={f.factor}>{f.factor}</li>
        ))}
      </ul>
    </div>
  );
}
