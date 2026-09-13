# Testing

Run the repeatable standard suite with `.venv/bin/python -m pytest`.

- Unit tests validate models, parsing, timeline construction, and frame data
  using fake providers.
- Integration tests exercise real Kokoro synthesis, FFmpeg audio mixing, and
  MP4 stream output.
- The starter-project render is the full-render check:
  `al-studio render projects/starter-project/project.json projects/starter-project/script.json --output output/reference-render`.

Run style/type checks after installing development tools: `ruff check app tests`
and `mypy app`.
