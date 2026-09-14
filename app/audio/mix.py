"""FFmpeg-backed deterministic dialogue mixing."""

import subprocess
from pathlib import Path

from app.script.timeline import TimelineEvent


class AudioMixer:
    def mix(self, timeline: tuple[TimelineEvent, ...], output_path: Path) -> Path:
        dialogue = [event for event in timeline if event.event_type == "dialogue"]
        if not dialogue:
            raise ValueError("timeline contains no dialogue audio")
        command = ["ffmpeg", "-y"]
        for event in dialogue:
            command.extend(["-i", event.payload["audio_path"]])
        filters = []
        labels = []
        for index, event in enumerate(dialogue):
            delay = round(event.start_seconds * 1000)
            label = f"a{index}"
            filters.append(f"[{index}:a]adelay={delay}|{delay}[{label}]")
            labels.append(f"[{label}]")
        filters.append(f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0[mixed]")
        filters.append("[mixed]loudnorm=I=-16:LRA=11:TP=-1.5[mix]")
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            command
            + [
                "-filter_complex",
                ";".join(filters),
                "-map",
                "[mix]",
                "-c:a",
                "pcm_s16le",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return output_path
