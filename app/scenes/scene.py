"""Scene configuration models."""

import math
from dataclasses import dataclass

ANIMATION_PRESETS = frozenset(
    {"fade-in", "fade-out", "slide-in", "bounce", "float", "pulse", "rotate", "shake"}
)
ANIMATION_EASINGS = frozenset({"linear", "ease-in", "ease-out", "ease-in-out"})
ANIMATION_DIRECTIONS = frozenset({"left", "right", "up", "down"})


def _validate_identifier(field_name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{field_name} must not have leading or trailing whitespace")


@dataclass(frozen=True, slots=True)
class CameraConfig:
    """Initial deterministic camera framing for a scene."""

    x: float = 0.0
    y: float = 0.0
    zoom: float = 1.0

    def __post_init__(self) -> None:
        for field_name, value in (("x", self.x), ("y", self.y), ("zoom", self.zoom)):
            if not isinstance(value, (int, float)) or isinstance(value, bool):
                raise TypeError(f"camera {field_name} must be a number")
        if self.zoom <= 0:
            raise ValueError("camera zoom must be greater than zero")


@dataclass(frozen=True, slots=True)
class SceneInstance:
    """One reusable visual asset placed in a scene coordinate system."""

    instance_id: str
    asset_id: str
    x: float
    y: float
    width: float
    height: float
    rotation: float = 0.0
    opacity: float = 1.0
    z_index: int = 0
    visible: bool = True

    def __post_init__(self) -> None:
        _validate_identifier("instance_id", self.instance_id)
        _validate_identifier("asset_id", self.asset_id)
        for field_name, value in (
            ("x", self.x),
            ("y", self.y),
            ("width", self.width),
            ("height", self.height),
            ("rotation", self.rotation),
            ("opacity", self.opacity),
        ):
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise TypeError(f"instance {field_name} must be a finite number")
        if self.width <= 0 or self.height <= 0:
            raise ValueError("instance width and height must be greater than zero")
        if not 0 <= self.opacity <= 1:
            raise ValueError("instance opacity must be between 0 and 1")
        if not isinstance(self.z_index, int) or isinstance(self.z_index, bool):
            raise TypeError("instance z_index must be an integer")
        if not isinstance(self.visible, bool):
            raise TypeError("instance visible must be a boolean")


@dataclass(frozen=True, slots=True)
class SceneAnimation:
    """A deterministic animation preset applied to one scene instance."""

    animation_id: str
    target_instance_id: str
    preset: str
    start_seconds: float
    duration_seconds: float
    easing: str = "ease-in-out"
    direction: str = "left"
    loop: bool = False

    def __post_init__(self) -> None:
        _validate_identifier("animation_id", self.animation_id)
        _validate_identifier("target_instance_id", self.target_instance_id)
        if self.preset not in ANIMATION_PRESETS:
            raise ValueError(
                f"animation preset must be one of: {', '.join(sorted(ANIMATION_PRESETS))}"
            )
        for field_name, value in (
            ("start_seconds", self.start_seconds),
            ("duration_seconds", self.duration_seconds),
        ):
            if (
                not isinstance(value, (int, float))
                or isinstance(value, bool)
                or not math.isfinite(value)
            ):
                raise TypeError(f"animation {field_name} must be a finite number")
        if self.start_seconds < 0:
            raise ValueError("animation start_seconds must not be negative")
        if self.duration_seconds <= 0:
            raise ValueError("animation duration_seconds must be greater than zero")
        if self.easing not in ANIMATION_EASINGS:
            raise ValueError(
                f"animation easing must be one of: {', '.join(sorted(ANIMATION_EASINGS))}"
            )
        if self.direction not in ANIMATION_DIRECTIONS:
            raise ValueError(
                f"animation direction must be one of: {', '.join(sorted(ANIMATION_DIRECTIONS))}"
            )
        if not isinstance(self.loop, bool):
            raise TypeError("animation loop must be a boolean")


@dataclass(frozen=True, slots=True)
class SceneConfig:
    """Scene identity and reusable visual asset references."""

    scene_id: str
    background_asset_id: str
    prop_asset_ids: tuple[str, ...] = ()
    instances: tuple[SceneInstance, ...] = ()
    animations: tuple[SceneAnimation, ...] = ()
    camera: CameraConfig = CameraConfig()

    def __post_init__(self) -> None:
        _validate_identifier("scene_id", self.scene_id)
        _validate_identifier("background_asset_id", self.background_asset_id)
        if not isinstance(self.prop_asset_ids, tuple):
            raise TypeError("prop_asset_ids must be a tuple")
        for asset_id in self.prop_asset_ids:
            _validate_identifier("prop_asset_ids item", asset_id)
        if not isinstance(self.instances, tuple):
            raise TypeError("instances must be a tuple")
        instance_ids = tuple(instance.instance_id for instance in self.instances)
        if len(instance_ids) != len(set(instance_ids)):
            raise ValueError("scene instance identifiers must be unique")
        if not isinstance(self.animations, tuple):
            raise TypeError("animations must be a tuple")
        animation_ids = tuple(animation.animation_id for animation in self.animations)
        if len(animation_ids) != len(set(animation_ids)):
            raise ValueError("scene animation identifiers must be unique")
        for animation in self.animations:
            if animation.target_instance_id not in instance_ids:
                raise ValueError(
                    f"animation references unknown instance: {animation.target_instance_id}"
                )
        if not isinstance(self.camera, CameraConfig):
            raise TypeError("camera must be a CameraConfig")
