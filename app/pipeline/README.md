# Pipeline Reliability

Renders use a user-selected output directory. Reusing the same inputs and
settings produces the same timeline, SVG frames, SRT, and FFmpeg command
structure; TTS model-version changes are the deliberate external source of
nondeterminism. `metadata.json` records dry-run or completion state.

If a render fails, inspect `metadata.json`, keep the output directory for its
intermediate dialogue, frames, and audio, fix the reported input/provider
error, then rerun the same command. `--dry-run` validates project assets and
records the planned render without generating media. `--verbose` prints the
stage order.
