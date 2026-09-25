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

## Asset Capability Manifest

A visual asset may include `capabilities.animations` in its project entry.
Each animation has a unique `id`, a positive `fps`, an optional `loop` default,
and one of these representations:

- `sprite_sheet`: one safe asset-relative `path` plus positive `frame_width`,
  `frame_height`, `frame_count`, and `columns` values.
- `frame_sequence`: a non-empty ordered `frames` list of safe asset-relative
  image paths.

Scene clips select a capability with `preset: "asset"` and
`asset_animation_id`. At scene time `t`, the deterministic frame index is
`floor((t - start_seconds) * fps)`. Looping clips apply modulo frame count;
non-looping clips hold their final frame. Sprite sheets are cropped through an
SVG view box, while frame sequences embed the resolved image for that index.
