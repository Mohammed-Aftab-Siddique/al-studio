"""FFmpeg-backed deterministic dialogue mixing."""

import subprocess
from pathlib import Path

from app.script.timeline import TimelineEvent


class AudioMixer:
    def mix(self, timeline: tuple[TimelineEvent, ...], output_path: Path) -> Path:
        if not timeline:
            raise ValueError("timeline must not be empty")
        duration = max(event.start_seconds + event.duration_seconds for event in timeline)
        audio_events = [
            event
            for event in timeline
            if event.event_type in {"dialogue", "ambience", "sound_effect"}
            and "audio_path" in event.payload
        ]
        command = [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-t",
            str(duration),
            "-i",
            "anullsrc=r=24000:cl=mono",
        ]
        for event in audio_events:
            command.extend(["-i", event.payload["audio_path"]])
        filters = [f"[0:a]atrim=duration={duration}[bed]"]
        labels = ["[bed]"]
        for index, event in enumerate(audio_events, 1):
            delay = round(event.start_seconds * 1000)
            label = f"a{index}"
            source = f"[{index}:a]"
            if event.event_type == "ambience":
                source += "aloop=loop=-1:size=2147483647,"
            elif event.event_type == "sound_effect":
                source += "apad,"
            filters.append(
                f"{source}atrim=duration={event.duration_seconds},adelay={delay}|{delay}[{label}]"
            )
            labels.append(f"[{label}]")
        filters.append(
            f"{''.join(labels)}amix=inputs={len(labels)}:normalize=0:duration=longest[mixed]"
        )
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
