from pathlib import Path

from app.audio.kokoro import KokoroVoiceEngine


def test_kokoro_generates_audio() -> None:
    output_path = Path("output/voice-tests/abstraction.wav")

    engine = KokoroVoiceEngine()

    result = engine.synthesize(
        text="This audio was generated through the AL Studio voice engine.",
        voice="am_adam",
        output_path=output_path,
    )

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
