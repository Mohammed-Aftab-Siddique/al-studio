"""FFmpeg MP4 composition from deterministic SVG frames and mixed audio."""

import subprocess
from pathlib import Path


class VideoCompositor:
    def compose(self, frame_pattern: Path, fps: int, audio_path: Path, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-framerate",
                str(fps),
                "-i",
                str(frame_pattern),
                "-i",
                str(audio_path),
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                "-c:a",
                "aac",
                "-shortest",
                str(output_path),
            ],
            check=True,
            capture_output=True,
            text=True,
        )
        return output_path
