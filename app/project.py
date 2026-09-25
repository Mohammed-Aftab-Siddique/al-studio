"""Versioned project configuration and safe reusable-asset resolution."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

from app.characters import AnimationConfig, CharacterConfig
from app.scenes import CameraConfig, SceneAnimation, SceneConfig, SceneInstance

CURRENT_SCHEMA_VERSION = 1
ASSET_KINDS = frozenset({"character", "scene", "prop", "audio", "music"})
IMAGE_EXTENSIONS = frozenset({".png", ".svg", ".webp"})
AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".ogg"})


class ProjectConfigError(ValueError):
    """Raised when a project configuration is invalid or unsupported."""


class AssetResolutionError(ProjectConfigError):
    """Raised when an asset cannot safely resolve from the configured root."""


def _required_string(data: dict[str, Any], field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ProjectConfigError(f"{field_name} must be a non-empty trimmed string")
    return value


@dataclass(frozen=True, slots=True)
class RenderSettings:
    width: int = 1280
    height: int = 720
    fps: int = 24

    def __post_init__(self) -> None:
        for field_name, value in (
            ("width", self.width),
            ("height", self.height),
            ("fps", self.fps),
        ):
            if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                raise ProjectConfigError(f"render {field_name} must be a positive integer")


@dataclass(frozen=True, slots=True)
class AssetConfig:
    asset_id: str
    kind: str
    path: str

    def __post_init__(self) -> None:
        _required_string({"asset_id": self.asset_id}, "asset_id")
        if self.kind not in ASSET_KINDS:
            raise ProjectConfigError(f"asset kind must be one of: {', '.join(sorted(ASSET_KINDS))}")
        _required_string({"path": self.path}, "path")
        candidate = PurePosixPath(self.path)
        if candidate.is_absolute() or ".." in candidate.parts:
            raise ProjectConfigError("asset path must stay within the asset root")


@dataclass(frozen=True, slots=True)
class ProjectConfig:
    name: str
    assets: tuple[AssetConfig, ...]
    characters: tuple[CharacterConfig, ...]
    scenes: tuple[SceneConfig, ...]
    render: RenderSettings = RenderSettings()
    schema_version: int = CURRENT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        _required_string({"name": self.name}, "name")
        if self.schema_version != CURRENT_SCHEMA_VERSION:
            raise ProjectConfigError(f"unsupported schema version: {self.schema_version}")
        self._validate_unique("asset", (asset.asset_id for asset in self.assets))
        self._validate_unique("character", (character.name for character in self.characters))
        self._validate_unique("scene", (scene.scene_id for scene in self.scenes))
        asset_by_id = {asset.asset_id: asset for asset in self.assets}
        for character in self.characters:
            if character.visual_asset_id is not None:
                self._validate_asset_reference(character.visual_asset_id, "character", asset_by_id)
        for scene in self.scenes:
            self._validate_asset_reference(scene.background_asset_id, "scene", asset_by_id)
            for prop_asset_id in scene.prop_asset_ids:
                self._validate_asset_reference(prop_asset_id, "prop", asset_by_id)
            for instance in scene.instances:
                asset = asset_by_id.get(instance.asset_id)
                if asset is None:
                    raise ProjectConfigError(f"unknown instance asset: {instance.asset_id}")
                if asset.kind not in {"character", "scene", "prop"}:
                    raise ProjectConfigError(
                        f"instance asset {instance.asset_id} must be a visual asset"
                    )

    @staticmethod
    def _validate_unique(label: str, values: Any) -> None:
        items = tuple(values)
        if len(items) != len(set(items)):
            raise ProjectConfigError(f"{label} identifiers must be unique")

    @staticmethod
    def _validate_asset_reference(
        asset_id: str, expected_kind: str, assets: dict[str, AssetConfig]
    ) -> None:
        asset = assets.get(asset_id)
        if asset is None:
            raise ProjectConfigError(f"unknown {expected_kind} asset: {asset_id}")
        if asset.kind != expected_kind:
            raise ProjectConfigError(f"asset {asset_id} must have kind {expected_kind}")

    @classmethod
    def from_dict(cls, raw: dict[str, Any]) -> ProjectConfig:
        if not isinstance(raw, dict):
            raise ProjectConfigError("project configuration must be an object")
        data = cls._upgrade_legacy(raw)
        if data.get("schema_version") != CURRENT_SCHEMA_VERSION:
            raise ProjectConfigError(f"unsupported schema version: {data.get('schema_version')}")
        return cls(
            name=_required_string(data, "name"),
            assets=tuple(cls._asset_from_dict(item) for item in cls._list(data, "assets")),
            characters=tuple(
                cls._character_from_dict(item) for item in cls._list(data, "characters")
            ),
            scenes=tuple(cls._scene_from_dict(item) for item in cls._list(data, "scenes")),
            render=cls._render_from_dict(data.get("render", {})),
        )

    @staticmethod
    def _upgrade_legacy(raw: dict[str, Any]) -> dict[str, Any]:
        data = dict(raw)
        version = data.get("schema_version", 0)
        if version == 0:
            data["schema_version"] = CURRENT_SCHEMA_VERSION
            data.setdefault("render", {})
            characters = []
            for character in data.get("characters", []):
                upgraded = dict(character)
                if "voice_id" not in upgraded and "voice" in upgraded:
                    upgraded["voice_id"] = upgraded.pop("voice")
                characters.append(upgraded)
            data["characters"] = characters
        return data

    @staticmethod
    def _list(data: dict[str, Any], field_name: str) -> list[dict[str, Any]]:
        value = data.get(field_name, [])
        if not isinstance(value, list) or not all(isinstance(item, dict) for item in value):
            raise ProjectConfigError(f"{field_name} must be a list of objects")
        return value

    @staticmethod
    def _asset_from_dict(data: dict[str, Any]) -> AssetConfig:
        return AssetConfig(
            asset_id=_required_string(data, "id"),
            kind=_required_string(data, "kind"),
            path=_required_string(data, "path"),
        )

    @staticmethod
    def _character_from_dict(data: dict[str, Any]) -> CharacterConfig:
        animation_data = data.get("animation", {})
        if not isinstance(animation_data, dict):
            raise ProjectConfigError("character animation must be an object")
        return CharacterConfig(
            name=_required_string(data, "name"),
            voice_id=_required_string(data, "voice_id"),
            visual_asset_id=data.get("visual_asset_id"),
            animation=AnimationConfig(
                idle_motion=animation_data.get("idle_motion", True),
                mouth_style=animation_data.get("mouth_style", "simple"),
            ),
        )

    @staticmethod
    def _scene_from_dict(data: dict[str, Any]) -> SceneConfig:
        camera_data = data.get("camera", {})
        if not isinstance(camera_data, dict):
            raise ProjectConfigError("scene camera must be an object")
        props = data.get("prop_asset_ids", [])
        if not isinstance(props, list):
            raise ProjectConfigError("prop_asset_ids must be a list")
        instances = data.get("instances", [])
        if not isinstance(instances, list) or not all(isinstance(item, dict) for item in instances):
            raise ProjectConfigError("instances must be a list of objects")
        animations = data.get("animations", [])
        if not isinstance(animations, list) or not all(
            isinstance(item, dict) for item in animations
        ):
            raise ProjectConfigError("animations must be a list of objects")
        return SceneConfig(
            scene_id=_required_string(data, "id"),
            background_asset_id=_required_string(data, "background_asset_id"),
            prop_asset_ids=tuple(props),
            instances=tuple(ProjectConfig._instance_from_dict(item) for item in instances),
            animations=tuple(ProjectConfig._animation_from_dict(item) for item in animations),
            camera=CameraConfig(
                x=camera_data.get("x", 0.0),
                y=camera_data.get("y", 0.0),
                zoom=camera_data.get("zoom", 1.0),
            ),
        )

    @staticmethod
    def _animation_from_dict(data: dict[str, Any]) -> SceneAnimation:
        return SceneAnimation(
            animation_id=_required_string(data, "id"),
            target_instance_id=_required_string(data, "target"),
            preset=_required_string(data, "preset"),
            start_seconds=cast(float, data.get("start_seconds", 0.0)),
            duration_seconds=cast(float, data.get("duration_seconds")),
            easing=data.get("easing", "ease-in-out"),
            direction=data.get("direction", "left"),
            loop=data.get("loop", False),
        )

    @staticmethod
    def _instance_from_dict(data: dict[str, Any]) -> SceneInstance:
        return SceneInstance(
            instance_id=_required_string(data, "id"),
            asset_id=_required_string(data, "asset_id"),
            x=cast(float, data.get("x")),
            y=cast(float, data.get("y")),
            width=cast(float, data.get("width")),
            height=cast(float, data.get("height")),
            rotation=data.get("rotation", 0.0),
            opacity=data.get("opacity", 1.0),
            z_index=data.get("z_index", 0),
            visible=data.get("visible", True),
        )

    @staticmethod
    def _render_from_dict(data: Any) -> RenderSettings:
        if not isinstance(data, dict):
            raise ProjectConfigError("render must be an object")
        return RenderSettings(
            width=data.get("width", 1280),
            height=data.get("height", 720),
            fps=data.get("fps", 24),
        )


@dataclass(slots=True)
class ProjectAssetManager:
    """Loads versioned projects and resolves asset-root-relative files."""

    asset_root: Path

    def __post_init__(self) -> None:
        self.asset_root = self.asset_root.resolve()

    def load_project(self, project_path: Path) -> ProjectConfig:
        try:
            raw = json.loads(project_path.read_text(encoding="utf-8"))
        except FileNotFoundError as error:
            raise ProjectConfigError(f"project file not found: {project_path}") from error
        except json.JSONDecodeError as error:
            raise ProjectConfigError(f"invalid JSON in project file: {project_path}") from error
        return ProjectConfig.from_dict(raw)

    def resolve_asset(self, asset: AssetConfig) -> Path:
        candidate = (self.asset_root / asset.path).resolve()
        if not candidate.is_relative_to(self.asset_root):
            raise AssetResolutionError(f"asset path escapes asset root: {asset.path}")
        if not candidate.is_file():
            raise AssetResolutionError(f"asset file not found: {asset.path}")
        allowed_extensions = (
            AUDIO_EXTENSIONS if asset.kind in {"audio", "music"} else IMAGE_EXTENSIONS
        )
        if candidate.suffix.lower() not in allowed_extensions:
            raise AssetResolutionError(
                f"asset {asset.asset_id} has incompatible extension {candidate.suffix or '<none>'} "
                f"for kind {asset.kind}"
            )
        return candidate

    def validate_assets(self, project: ProjectConfig) -> dict[str, Path]:
        return {asset.asset_id: self.resolve_asset(asset) for asset in project.assets}
