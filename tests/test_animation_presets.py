import pytest

from app.animation import evaluate_animation, evaluate_animations
from app.scenes import SceneAnimation


def clip(**overrides: object) -> SceneAnimation:
    values = {
        "animation_id": "motion",
        "target_instance_id": "hero",
        "preset": "slide-in",
        "start_seconds": 0,
        "duration_seconds": 2,
        "easing": "linear",
        "direction": "left",
        "loop": False,
    }
    values.update(overrides)
    return SceneAnimation(**values)  # type: ignore[arg-type]


def test_universal_animation_presets_are_deterministic() -> None:
    slide = evaluate_animation(clip(), 1)
    fade = evaluate_animation(clip(preset="fade-in"), 1)
    rotate = evaluate_animation(clip(preset="rotate", direction="right"), 1)

    assert slide.x == pytest.approx(-90)
    assert slide.y == 0
    assert fade.opacity == pytest.approx(0.5)
    assert rotate.rotation == pytest.approx(180)


def test_easing_looping_and_combined_transforms() -> None:
    animations = (
        clip(animation_id="move", duration_seconds=1, loop=True),
        clip(
            animation_id="fade",
            preset="fade-in",
            duration_seconds=2,
            easing="ease-in",
        ),
    )

    combined = evaluate_animations("hero", animations, 2.5)

    assert combined.x == pytest.approx(-90)
    assert combined.opacity == 1
    assert evaluate_animations("other", animations, 0.5).x == 0


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("preset", "teleport", "animation preset"),
        ("duration_seconds", 0, "duration_seconds"),
        ("start_seconds", -1, "start_seconds"),
        ("easing", "elastic", "animation easing"),
        ("direction", "diagonal", "animation direction"),
    ],
)
def test_animation_clip_validation(field: str, value: object, message: str) -> None:
    with pytest.raises((TypeError, ValueError), match=message):
        clip(**{field: value})
