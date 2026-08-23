"""Channel splitting. The recordings already separate agent (left) from customer
(right) — this is the whole diarization step. No ML diarization model involved."""
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class ChannelPaths:
    agent_wav: Path
    customer_wav: Path


def split_channels(mp3_path: Path, out_dir: Path, sample_rate: int = 16000) -> ChannelPaths:
    """Split a stereo call recording into two mono wavs, resampled up from the
    original 8kHz telephone quality to `sample_rate` for the ASR model.

    Left channel -> agent, right channel -> customer, per the dataset's
    documented convention. Requires ffmpeg on PATH (already present in the
    backend Docker image).
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    agent_wav = out_dir / f"{mp3_path.stem}.agent.wav"
    customer_wav = out_dir / f"{mp3_path.stem}.customer.wav"

    cmd = [
        "ffmpeg", "-y", "-i", str(mp3_path),
        "-filter_complex", "[0:a]channelsplit=channel_layout=stereo[left][right]",
        "-map", "[left]", "-ar", str(sample_rate), "-ac", "1", str(agent_wav),
        "-map", "[right]", "-ar", str(sample_rate), "-ac", "1", str(customer_wav),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"ffmpeg failed to split {mp3_path}:\n{result.stderr}")

    return ChannelPaths(agent_wav=agent_wav, customer_wav=customer_wav)
