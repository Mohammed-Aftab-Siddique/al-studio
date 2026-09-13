# AL Studio

Local-first, script-driven 2D animation rendering. The starter project builds
a voiced SVG animation, SRT captions, mixed WAV audio, and MP4 output.

## Install

Requires Python 3.12, FFmpeg, and eSpeak NG. Create a virtual environment,
then run `pip install -e .`.

## Quick start

`al-studio validate projects/starter-project/project.json`

`al-studio render projects/starter-project/project.json projects/starter-project/script.json --output output/reference-render --verbose`

Use `--dry-run` to validate and record a plan without media generation.

## CLI

- `validate PROJECT` validates project data and assets.
- `inspect-assets PROJECT` lists resolved reusable assets.
- `voice-preview --text TEXT --voice ID --output FILE.wav` synthesizes WAV.
- `render PROJECT SCRIPT` produces dialogue, frames, audio, captions, and MP4.

Project assets are described in `projects/starter-project/project.json`; the
versioned script format is documented in `app/script/FORMAT.md`.

## Tests and release notes

See `TESTING.md`, `BENCHMARK.md`, and `LICENSES.md`. Generated media stays out
of Git. If a render fails, retain its output folder, inspect `metadata.json`,
fix the reported input/provider issue, then rerun.
