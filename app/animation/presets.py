"""Deterministic transform animation presets shared by rendered scene instances."""

from __future__ import annotations

import math
from dataclasses import dataclass

from app.scenes import SceneAnimation


@dataclass(frozen=True, slots=True)
class AnimationTransform:
    x: float = 0.0
    y: float = 0.0
    scale: float = 1.0
    rotation: float = 0.0
    opacity: float = 1.0


def evaluate_animations(
    target_instance_id: str,
    animations: tuple[SceneAnimation, ...],
    time_seconds: float,
) -> AnimationTransform:
    """Combine all preset transforms targeting an instance at a scene-local time."""
    x = y = rotation = 0.0
    scale = opacity = 1.0
    for animation in animations:
        if animation.target_instance_id != target_instance_id:
            continue
        current = evaluate_animation(animation, time_seconds)
        x += current.x
        y += current.y
        rotation += current.rotation
        scale *= current.scale
        opacity *= current.opacity
    return AnimationTransform(x, y, scale, rotation, max(0.0, min(1.0, opacity)))


def evaluate_animation(animation: SceneAnimation, time_seconds: float) -> AnimationTransform:
    raw_progress = (time_seconds - animation.start_seconds) / animation.duration_seconds
    if animation.loop and raw_progress >= 0:
        raw_progress %= 1.0
    else:
        raw_progress = max(0.0, min(1.0, raw_progress))
    progress = _ease(raw_progress, animation.easing)
    preset = animation.preset

    if preset == "fade-in":
        return AnimationTransform(opacity=progress)
    if preset == "fade-out":
        return AnimationTransform(opacity=1.0 - progress)
    if preset == "slide-in":
        distance = 180.0 * (1.0 - progress)
        offsets = {
            "left": (-distance, 0.0),
            "right": (distance, 0.0),
            "up": (0.0, -distance),
            "down": (0.0, distance),
        }
        return AnimationTransform(
            x=offsets[animation.direction][0], y=offsets[animation.direction][1]
        )
    if preset == "bounce":
        return AnimationTransform(y=-55.0 * math.sin(math.pi * progress))
    if preset == "float":
        return AnimationTransform(y=-24.0 * math.sin(2.0 * math.pi * progress))
    if preset == "pulse":
        return AnimationTransform(scale=1.0 + 0.14 * math.sin(math.pi * progress))
    if preset == "rotate":
        sign = -1.0 if animation.direction in {"left", "up"} else 1.0
        return AnimationTransform(rotation=sign * 360.0 * progress)
    if preset == "shake":
        return AnimationTransform(x=18.0 * math.sin(8.0 * math.pi * progress))
    if preset == "asset":
        return AnimationTransform()
    raise ValueError(f"unsupported animation preset: {preset}")


def _ease(progress: float, easing: str) -> float:
    if easing == "linear":
        return progress
    if easing == "ease-in":
        return progress * progress
    if easing == "ease-out":
        return 1.0 - (1.0 - progress) ** 2
    if easing == "ease-in-out":
        return (
            2.0 * progress * progress
            if progress < 0.5
            else 1.0 - (-2.0 * progress + 2.0) ** 2 / 2.0
        )
    raise ValueError(f"unsupported easing: {easing}")
