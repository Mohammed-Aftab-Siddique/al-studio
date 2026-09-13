# AL Studio — Current State

> A concise, repository-verified snapshot of the implementation.
>
> Last verified: 2026-09-13

## What AL Studio Is

AL Studio is an open-source, local-first, script-driven 2D animation
studio. Its intended output is a rendered video assembled from reusable
characters, scenes, dialogue, animation, sound, subtitles, and rendering
settings.

The architecture is deliberately deterministic: reusable assets, scene
layout, timing, and character identity should not depend on regenerating
content with AI for every video. AI is planned as an optional supporting
tool, not the foundation of the animation pipeline.

## Implementation Status

The repository is currently in **Phase 2: Voice Engine**.

Implemented and verified:

- Python package configuration for `al-studio` (Python `>=3.12,<3.13`).
- Stable top-level directory structure for the planned animation pipeline.
- A generic `VoiceEngine` abstract interface at `app/audio/voice.py`.
- `KokoroVoiceEngine` at `app/audio/kokoro.py`, isolated behind that
  interface so a different TTS engine can be added later.
- CPU-default Kokoro synthesis with a configurable language code and
  voice ID.
- Mono PCM-16 WAV output at 24 kHz; parent output directories are created
  automatically.
- A real integration test that synthesizes audio with the `am_adam` voice
  and verifies that the returned WAV file exists and is non-empty.
- A provider-neutral `CharacterConfig` model that persists a character name
  and voice ID, validates both values, and does not import Kokoro.
- Nine fast unit tests for character configuration validation.

Not implemented yet:

- Script format and dialogue orchestration.
- Character assets and 2D animation.
- Scene, audio-mixing, subtitle, compositor/video, CLI, and automation
  systems.

The directories for those areas exist as scaffolding but contain no
implementation files at this point.

## Verification

Last run on 2026-09-13:

```text
.venv/bin/python -m pytest tests/test_voice_engine.py -v
1 passed, 5 warnings
```

The test performs actual Kokoro synthesis and passed. The five warnings
come from PyTorch/Misaki dependencies (deprecations and an LSTM dropout
configuration warning), rather than AL Studio code.

## Current Repository Notes

- Recent committed checkpoints include the project setup, Kokoro test, and
  voice-engine abstraction.
- `PROGRESS.md` is an untracked detailed development log.
- `README.md` currently has no content.
- Generated media is ignored by Git; voice test output is written beneath
  `output/voice-tests/`.

## Immediate Next Step

Add Voice Engine validation and fast unit tests using a fake provider. This
will make invalid text, voice IDs, output paths, and provider failures easier
to diagnose before the project and script layers begin using the engine.
