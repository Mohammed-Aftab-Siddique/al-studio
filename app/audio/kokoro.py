from pathlib import Path
from typing import Any

import soundfile as sf
from kokoro import KPipeline

from .voice import VoiceEngine, VoiceSynthesisError


class KokoroVoiceEngine(VoiceEngine):
    """Kokoro implementation of the AL Studio voice engine."""

    SAMPLE_RATE = 24000

    def __init__(
        self,
        lang_code: str = "a",
        device: str = "cpu",
        pipeline: Any | None = None,
    ) -> None:
        self.pipeline = pipeline or KPipeline(lang_code=lang_code, device=device)

    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> Path:
        self.validate_synthesis_request(text, voice, output_path)
        if output_path.suffix.lower() != ".wav":
            raise ValueError("Kokoro output_path must use the .wav extension")

        output_path.parent.mkdir(parents=True, exist_ok=True)

        try:
            with sf.SoundFile(
                output_path,
                mode="w",
                samplerate=self.SAMPLE_RATE,
                channels=1,
                subtype="PCM_16",
            ) as audio_file:
                for result in self.pipeline(text, voice=voice):
                    audio_file.write(result.audio.numpy())
        except Exception as error:
            raise VoiceSynthesisError(
                f"Kokoro failed to synthesize voice {voice!r} to {output_path}"
            ) from error

        return output_path
