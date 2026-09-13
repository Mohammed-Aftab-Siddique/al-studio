# Deterministic Frame Format

The initial 2D render representation is self-contained SVG frames. This
requires no GPU or rendering-library dependency, embeds reusable assets as
data URIs, and supports deterministic transforms, camera framing, props, and
dialogue-timed mouth states. `FrameRenderer.render_sequence()` writes one SVG
per frame; a later compositor will convert the sequence to final video.
