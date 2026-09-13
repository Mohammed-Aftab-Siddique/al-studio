"""Scene configuration models."""

from dataclasses import dataclass


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
class SceneConfig:
    """Scene identity and reusable visual asset references."""

    scene_id: str
    background_asset_id: str
    prop_asset_ids: tuple[str, ...] = ()
    camera: CameraConfig = CameraConfig()

    def __post_init__(self) -> None:
        _validate_identifier("scene_id", self.scene_id)
        _validate_identifier("background_asset_id", self.background_asset_id)
        if not isinstance(self.prop_asset_ids, tuple):
            raise TypeError("prop_asset_ids must be a tuple")
        for asset_id in self.prop_asset_ids:
            _validate_identifier("prop_asset_ids item", asset_id)
        if not isinstance(self.camera, CameraConfig):
            raise TypeError("camera must be a CameraConfig")
