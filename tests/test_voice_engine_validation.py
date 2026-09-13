from pathlib import Path

import numpy as np
import pytest

from app.audio.kokoro import KokoroVoiceEngine
from app.audio.voice import VoiceSynthesisError


class FakeAudio:
    def numpy(self) -> np.ndarray:
        return np.zeros(240, dtype=np.float32)


class FakeResult:
    audio = FakeAudio()


class FakeKokoroPipeline:
    def __init__(self, should_fail: bool = False) -> None:
        self.should_fail = should_fail
        self.calls: list[tuple[str, str]] = []

    def __call__(self, text: str, voice: str):
        self.calls.append((text, voice))
        if self.should_fail:
            raise RuntimeError("provider unavailable")
        yield FakeResult()


def test_kokoro_engine_synthesizes_with_a_fake_pipeline(tmp_path: Path) -> None:
    pipeline = FakeKokoroPipeline()
    output_path = tmp_path / "line.wav"
    engine = KokoroVoiceEngine(pipeline=pipeline)

    result = engine.synthesize("Hello there.", "am_adam", output_path)

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
    assert pipeline.calls == [("Hello there.", "am_adam")]


@pytest.mark.parametrize("text", ["", "   ", 1])
def test_kokoro_engine_rejects_invalid_text_before_calling_provider(
    tmp_path: Path,
    text: object,
) -> None:
    pipeline = FakeKokoroPipeline()
    engine = KokoroVoiceEngine(pipeline=pipeline)

    with pytest.raises((TypeError, ValueError)):
        engine.synthesize(text, "am_adam", tmp_path / "line.wav")  # type: ignore[arg-type]

    assert pipeline.calls == []


@pytest.mark.parametrize("voice", ["", "   ", 1])
def test_kokoro_engine_rejects_invalid_voice_before_calling_provider(
    tmp_path: Path,
    voice: object,
) -> None:
    pipeline = FakeKokoroPipeline()
    engine = KokoroVoiceEngine(pipeline=pipeline)

    with pytest.raises((TypeError, ValueError)):
        engine.synthesize("Hello there.", voice, tmp_path / "line.wav")  # type: ignore[arg-type]

    assert pipeline.calls == []


def test_kokoro_engine_rejects_non_path_output(tmp_path: Path) -> None:
    engine = KokoroVoiceEngine(pipeline=FakeKokoroPipeline())

    with pytest.raises(TypeError, match="output_path must be a pathlib.Path"):
        engine.synthesize("Hello there.", "am_adam", str(tmp_path / "line.wav"))  # type: ignore[arg-type]


def test_kokoro_engine_rejects_non_wav_output_path(tmp_path: Path) -> None:
    engine = KokoroVoiceEngine(pipeline=FakeKokoroPipeline())

    with pytest.raises(ValueError, match="must use the .wav extension"):
        engine.synthesize("Hello there.", "am_adam", tmp_path / "line.mp3")


def test_kokoro_engine_wraps_provider_failures(tmp_path: Path) -> None:
    engine = KokoroVoiceEngine(pipeline=FakeKokoroPipeline(should_fail=True))

    with pytest.raises(VoiceSynthesisError, match="Kokoro failed to synthesize") as error:
        engine.synthesize("Hello there.", "am_adam", tmp_path / "line.wav")

    assert isinstance(error.value.__cause__, RuntimeError)
