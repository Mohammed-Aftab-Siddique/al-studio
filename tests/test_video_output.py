from pathlib import Path
import subprocess

import numpy as np
import soundfile as sf

from app.audio.mix import AudioMixer
from app.script.timeline import TimelineEvent
from app.video.compositor import VideoCompositor
from app.video.subtitles import SubtitleWriter


def _timeline(tmp_path: Path) -> tuple[TimelineEvent, ...]:
    wav = tmp_path / "line.wav"
    sf.write(wav, np.zeros(2400, dtype=np.float32), 24000)
    return (TimelineEvent("room-000", "dialogue", "room", 0.0, 0.1, {"audio_path": str(wav), "caption": "Hello", "speaker": "Alex", "text": "Hello"}),)


def test_audio_mixer_and_subtitle_writer_create_timed_artifacts(tmp_path: Path) -> None:
    timeline = _timeline(tmp_path)
    mixed = AudioMixer().mix(timeline, tmp_path / "mix.wav")
    subtitles = SubtitleWriter().write(timeline, tmp_path / "captions.srt")
    assert sf.info(mixed).duration == 0.1
    assert subtitles.read_text(encoding="utf-8") == "1\n00:00:00,000 --> 00:00:00,100\nHello\n"


def test_compositor_creates_mp4_with_audio_and_video(tmp_path: Path) -> None:
    timeline = _timeline(tmp_path)
    audio = AudioMixer().mix(timeline, tmp_path / "mix.wav")
    frame = '<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64"><rect width="64" height="64" fill="blue"/></svg>'
    for index in range(2):
        (tmp_path / f"frame-{index:06d}.svg").write_text(frame, encoding="utf-8")
    output = VideoCompositor().compose(tmp_path / "frame-%06d.svg", 10, audio, tmp_path / "final.mp4")
    streams = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=codec_type", "-of", "csv=p=0", str(output)], check=True, capture_output=True, text=True).stdout.splitlines()
    assert output.is_file() and output.stat().st_size > 0
    assert set(streams) == {"audio", "video"}
