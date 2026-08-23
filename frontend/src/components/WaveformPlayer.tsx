// Playable waveform (wavesurfer.js) that TranscriptPanel and EvidenceChip
// seek into when a turn or a citation is clicked.
interface Props {
  audioUrl: string;
}

export default function WaveformPlayer({ audioUrl }: Props) {
  // TODO: wavesurfer.js instance; expose a seekTo(seconds) via ref/context
  // so sibling components can jump the playhead.
  return <div className="p-4 border rounded">TODO: waveform for {audioUrl || "(no audio)"}</div>;
}
