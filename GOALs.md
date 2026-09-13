# AL Studio — Goals and Delivery Plan

> Status snapshot and phased roadmap toward a local-first, script-driven
> 2D animation studio.
>
> Last updated: 2026-09-13

## Definition of a First Complete Release

AL Studio has reached its first complete release when a user can define
characters, scenes, and dialogue in a documented project format; render a
short multi-character 2D cartoon locally from the CLI; and receive an MP4
with synchronized voices, animation, ambience/sound effects, and subtitles.

The release must use reusable character and scene assets, persist character
voice identities, run on the current CPU-focused development environment,
and provide a reproducible example project with automated tests for the
core pipeline.

## Goals

### Foundation

- [x] Create the repository, Python package, virtual environment, and
  stable directory layout.
- [x] Configure generated-output and media ignore rules.
- [x] Establish local development tooling, including FFmpeg and eSpeak NG.
- [x] Define the local-first, deterministic 2D architecture and the
  reusable-asset approach.

### Voice Engine

- [x] Evaluate and install CPU-capable Kokoro TTS.
- [x] Verify multiple distinct Kokoro voices through real WAV generation.
- [x] Define the TTS-independent `VoiceEngine` interface.
- [x] Implement `KokoroVoiceEngine` with 24 kHz mono PCM-16 WAV output.
- [x] Add and pass an integration test that performs real synthesis.
- [x] Add character voice configuration that persists a voice ID without
  exposing Kokoro details to the character model.
- [x] Add input validation and useful errors for invalid text, voice IDs,
  output paths, and synthesis failures.
- [x] Add fast unit tests with a fake voice engine, keeping real Kokoro
  synthesis as a slower integration test.

### Project, Character, and Asset Model

- [ ] Define versioned project, character, scene, and asset configuration
  schemas (including defaults and validation).
- [ ] Implement character definitions: name, visual asset references,
  voice configuration, and animation parameters.
- [ ] Implement a project/asset manager that resolves files safely and
  reports missing or incompatible assets clearly.
- [ ] Provide a small reusable starter asset set and example project.
- [ ] Add tests for schema validation, asset resolution, and backwards
  compatibility rules.

### Script and Dialogue

- [ ] Design and document a human-editable script format for scenes,
  dialogue, actions, ambience, and captions.
- [ ] Parse and validate scripts into an internal timeline model.
- [ ] Resolve dialogue speakers to configured characters and synthesize
  their voice lines through `VoiceEngine`.
- [ ] Measure generated audio durations and construct deterministic dialogue
  timing.
- [ ] Add parser, validation, and timeline tests with fixture projects.

### 2D Animation and Scenes

- [ ] Choose and document the initial render representation and libraries
  for 2D assets, transforms, and frame generation.
- [ ] Implement reusable character rig/state primitives: position, scale,
  facing direction, visibility, expressions, and simple poses.
- [ ] Implement deterministic dialogue animation, beginning with timed mouth
  movement and optional idle motion.
- [ ] Implement scene backgrounds, props, camera framing, and timeline-based
  transitions.
- [ ] Add frame-level regression tests for core animation and scene behavior.

### Audio, Captions, and Video Output

- [ ] Implement an audio timeline that aligns dialogue, ambience, sound
  effects, and optional music.
- [ ] Normalize/mix audio with predictable levels and export a final track.
- [ ] Generate time-aligned subtitles from dialogue and support at least one
  standard subtitle output (for example, SRT).
- [ ] Composite animation frames, mixed audio, and optional burned-in
  subtitles into MP4 through FFmpeg.
- [ ] Verify output duration, stream presence, and subtitle/timing behavior
  with automated integration tests.

### Pipeline, CLI, and Reliability

- [ ] Implement an orchestrating pipeline with explicit stages, structured
  errors, and a predictable output directory per render.
- [ ] Build a CLI for project validation, asset inspection, voice preview,
  and rendering.
- [ ] Add dry-run and verbose modes that explain planned work without
  producing final media.
- [ ] Make reruns deterministic where inputs and settings are unchanged;
  document any deliberate nondeterminism.
- [ ] Add logging, render metadata, and failure recovery guidance.

### Quality and Release Readiness

- [ ] Add a test strategy separating unit, integration, and full-render
  tests; make the standard test command documented and repeatable.
- [ ] Add code formatting, linting, type checking, and CI once the workflow
  is stable.
- [ ] Benchmark the reference project on CPU and document expected runtime,
  disk use, and limitations.
- [ ] Write a complete README: installation, prerequisites, quick start,
  project format, CLI reference, asset licensing, and troubleshooting.
- [ ] Publish a versioned example project and validate that a clean setup
  can render it end-to-end.
- [ ] Review licenses for bundled assets and third-party dependencies before
  public release.

### Optional AI Enhancements (After the Deterministic Pipeline Works)

- [ ] Add opt-in helpers for script drafting, background concepts, character
  concepts, and creative suggestions.
- [ ] Ensure every AI-generated result can be saved as an editable reusable
  asset or configuration, rather than becoming a mandatory render-time
  dependency.
- [ ] Keep AI providers behind interfaces and document local/offline
  alternatives where practical.

## Recommended Execution Order

1. Define the project/character/scene schemas and create one example
   project.
2. Implement the script parser and dialogue timeline, then connect it to
   real voice synthesis.
3. Deliver a minimal vertical slice: one static scene, one character,
   spoken dialogue, simple mouth animation, captions, and an MP4.
4. Expand the vertical slice to multiple characters, scenes, props,
   ambience, sound effects, and transitions.
5. Harden the pipeline and CLI, then complete documentation, test coverage,
   benchmarks, and release checks.
6. Add optional AI assistance only after the deterministic render path is
   useful on its own.

## Near-Term Milestone

**Milestone: Render a minimal dialogue scene.**

Success means an example project with one configured character and voice,
one background, a short dialogue line, visible timed mouth movement,
generated subtitle timing, and a locally rendered MP4. It is the smallest
end-to-end proof that the architecture is working before broader features
are added.
