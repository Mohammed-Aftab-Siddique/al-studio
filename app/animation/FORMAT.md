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

## Layered Rig Capability

An asset can also declare `capabilities.rig` with a positive `canvas_width`
and `canvas_height`, one or more image `parts`, and named `poses`. Each part
defines its asset-relative image path, parent-relative position and size,
local pivot, optional `parent_id`, and integer layer. Parent references must
form an acyclic hierarchy. All part files are resolved and type-checked before
rendering.

A pose contains a suggested positive `duration_seconds`, a loop default, and
at least two strictly ordered keyframes spanning normalized time `0` through
`1`. Keyframes map part IDs to local translation, rotation, scale, and opacity.
Values are linearly interpolated between adjacent keyframes; omitted part
transforms are neutral at that keyframe.

Scene clips select a pose with `preset: "rig"` and `rig_pose_id`. The browser
and SVG renderer calculate the same normalized clip progress, interpolate the
same transforms, and recursively apply parent transforms to child parts.
Non-looping clips hold the final pose; looping clips wrap at their editable
scene duration. Universal whole-instance presets can run at the same time.
