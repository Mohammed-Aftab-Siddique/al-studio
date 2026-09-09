from pathlib import Path

import soundfile as sf
from kokoro import KPipeline

from .voice import VoiceEngine


class KokoroVoiceEngine(VoiceEngine):
    """Kokoro implementation of the AL Studio voice engine."""

    SAMPLE_RATE = 24000

    def __init__(self, lang_code: str = "a", device: str = "cpu") -> None:
        self.pipeline = KPipeline(
            lang_code=lang_code,
            device=device,
        )

    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sf.SoundFile(
            output_path,
            mode="w",
            samplerate=self.SAMPLE_RATE,
            channels=1,
            subtype="PCM_16",
        ) as audio_file:
            for result in self.pipeline(text, voice=voice):
                audio_file.write(result.audio.numpy())

        return output_path
