from pathlib import Path

import soundfile as sf
from kokoro import KPipeline


OUTPUT_DIR = Path("output/voice-tests")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

pipeline = KPipeline(lang_code="a", device="cpu")

tests = {
    "adam": ("am_adam", "Hello, my friends. It's good to see you."),
    "michael": ("am_michael", "Hello, my friends. It's good to see you."),
    "puck": ("am_puck", "Hello, my friends. It's good to see you."),
}

for name, (voice, text) in tests.items():
    output_path = OUTPUT_DIR / f"{name}.wav"

    with sf.SoundFile(
        output_path,
        mode="w",
        samplerate=24000,
        channels=1,
        subtype="PCM_16",
    ) as audio_file:
        for result in pipeline(text, voice=voice):
            audio_file.write(result.audio.numpy())

    print(f"Created: {output_path}")
