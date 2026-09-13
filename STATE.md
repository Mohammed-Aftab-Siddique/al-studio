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

The repository has completed the **Voice Engine**, **Project/Asset Model**,
and **Script and Dialogue** milestones. Deterministic scene and animation
rendering is next.

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
- Provider-neutral validation for synthesis text, voice IDs, and output
  paths, plus a contextual `VoiceSynthesisError` for provider failures.
- Ten fast voice-engine tests that use an injected fake Kokoro pipeline.
- Versioned project, character, scene, render, and asset models with safe
  defaults, validation, and schema-version 0-to-1 compatibility upgrades.
- A project/asset manager that loads JSON, resolves only asset-root-relative
  files, and reports missing or incompatible assets clearly.
- Reusable starter character, scene, and prop SVG assets plus a validated
  example project at `projects/starter-project/project.json`.
- Project-model tests for schema validation, asset resolution, and backwards
  compatibility.
- A documented versioned JSON script format supporting dialogue, actions,
  ambience, sound effects, and captions.
- Script validation and a deterministic timeline builder that resolves
  project characters, synthesizes dialogue through `VoiceEngine`, measures
  WAV duration, and emits timestamped events.

Not implemented yet:

- 2D animation and scene rendering.
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

Implement deterministic 2D scene and character rendering, beginning with the
starter background, Alex asset, and dialogue-timed mouth animation. This is
the visual half of the first end-to-end MP4 vertical slice.
