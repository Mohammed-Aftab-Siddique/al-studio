# Deterministic Frame Format

The initial 2D render representation is self-contained SVG frames. This
requires no GPU or rendering-library dependency, embeds reusable assets as
data URIs, and supports deterministic transforms, camera framing, props, and
dialogue-timed mouth states. `FrameRenderer.render_sequence()` writes one SVG
per frame; a later compositor will convert the sequence to final video.

Scene instances can also own deterministic preset animation clips. A clip
stores its target instance, preset, scene-local start time, duration, easing,
direction, and loop flag. Supported presets are `fade-in`, `fade-out`,
`slide-in`, `bounce`, `float`, `pulse`, `rotate`, and `shake`. Preset transforms
are evaluated for each frame and composed with the instance's saved transform;
no browser-only CSS animation is used in the rendered output.
