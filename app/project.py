"""Versioned project configuration and safe reusable-asset resolution."""

from __future__ import annotations

import json
import math
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, cast

from app.characters import AnimationConfig, CharacterConfig
from app.scenes import CameraConfig, SceneAnimation, SceneConfig, SceneInstance

CURRENT_SCHEMA_VERSION = 1
ASSET_KINDS = frozenset({"character", "scene", "prop", "audio", "music"})
IMAGE_EXTENSIONS = frozenset({".png", ".svg", ".webp"})
AUDIO_EXTENSIONS = frozenset({".wav", ".mp3", ".ogg"})
ASSET_ANIMATION_TYPES = frozenset({"sprite_sheet", "frame_sequence"})


class ProjectConfigError(ValueError):
    """Raised when a project configuration is invalid or unsupported."""


class AssetResolutionError(ProjectConfigError):
    """Raised when an asset cannot safely resolve from the configured root."""


def _required_string(data: dict[str, Any], field_name: str) -> str:
    value = data.get(field_name)
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ProjectConfigError(f"{field_name} must be a non-empty trimmed string")
    return value


def _validate_asset_path(path: str, label: str = "asset path") -> None:
    _required_string({"path": path}, "path")
    candidate = PurePosixPath(path)
    if candidate.is_absolute() or ".." in candidate.parts:
        raise ProjectConfigError(f"{label} must stay within the asset root")


def capability_asset_key(asset_id: str, animation_id: str, frame: int = 0) -> str:
    """Return the internal lookup key for a resolved capability image."""
    return f"@animation:{asset_id}:{animation_id}:{frame}"


def rig_part_asset_key(asset_id: str, part_id: str) -> str:
    """Return the internal lookup key for a resolved rig-part image."""
    return f"@rig:{asset_id}:{part_id}"


@dataclass(frozen=True, slots=True)
class AssetAnimationCapability:
    """A visual animation declared by an asset capability manifest."""

    animation_id: str
    animation_type: str
    fps: float
    loop: bool = True
    path: str | None = None
    frames: tuple[str, ...] = ()
    frame_width: int | None = None
    frame_height: int | None = None
    frame_count: int | None = None
    columns: int | None = None

    def __post_init__(self) -> None:
        _required_string({"animation_id": self.animation_id}, "animation_id")
        if self.animation_type not in ASSET_ANIMATION_TYPES:
            raise ProjectConfigError(
                f"asset animation type must be one of: {', '.join(sorted(ASSET_ANIMATION_TYPES))}"
            )
        if not isinstance(self.fps, (int, float)) or isinstance(self.fps, bool) or self.fps <= 0:
            raise ProjectConfigError("asset animation fps must be a positive number")
        if not isinstance(self.loop, bool):
            raise ProjectConfigError("asset animation loop must be a boolean")
        if self.animation_type == "sprite_sheet":
            if self.path is None:
                raise ProjectConfigError("sprite-sheet animation requires path")
            _validate_asset_path(self.path, "sprite-sheet path")
            for field_name, value in (
                ("frame_width", self.frame_width),
                ("frame_height", self.frame_height),
                ("frame_count", self.frame_count),
                ("columns", self.columns),
            ):
                if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
                    raise ProjectConfigError(
                        f"sprite-sheet {field_name} must be a positive integer"
                    )
            assert self.columns is not None and self.frame_count is not None
            if self.columns > self.frame_count:
                raise ProjectConfigError("sprite-sheet columns must not exceed frame_count")
        else:
            if not self.frames:
                raise ProjectConfigError("frame-sequence animation requires frames")
            for frame in self.frames:
                _validate_asset_path(frame, "frame-sequence path")

    @property
    def total_frames(self) -> int:
        return self.frame_count or len(self.frames)


def _finite_number(value: Any, label: str, *, positive: bool = False) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or not math.isfinite(value):
        raise ProjectConfigError(f"{label} must be a finite number")
    if positive and value <= 0:
        raise ProjectConfigError(f"{label} must be greater than zero")
    return float(value)


@dataclass(frozen=True, slots=True)
class RigPart:
    """One image layer attached to an optional parent in a 2D rig."""

    part_id: str
    path: str
    x: float
    y: float
    width: float
    height: float
    pivot_x: float
    pivot_y: float
    parent_id: str | None = None
    z_index: int = 0

    def __post_init__(self) -> None:
        _required_string({"part_id": self.part_id}, "part_id")
        _validate_asset_path(self.path, "rig part path")
        for label, value, positive in (
            ("rig part x", self.x, False),
            ("rig part y", self.y, False),
            ("rig part width", self.width, True),
            ("rig part height", self.height, True),
            ("rig part pivot_x", self.pivot_x, False),
            ("rig part pivot_y", self.pivot_y, False),
        ):
            _finite_number(value, label, positive=positive)
        if self.parent_id is not None:
            _required_string({"parent_id": self.parent_id}, "parent_id")
        if not isinstance(self.z_index, int) or isinstance(self.z_index, bool):
            raise ProjectConfigError("rig part z_index must be an integer")


@dataclass(frozen=True, slots=True)
class RigPartTransform:
    """A keyframed local transform for one rig part."""

    x: float = 0.0
    y: float = 0.0
    rotation: float = 0.0
    scale: float = 1.0
    opacity: float = 1.0

    def __post_init__(self) -> None:
        for label, value in (
            ("rig transform x", self.x),
            ("rig transform y", self.y),
            ("rig transform rotation", self.rotation),
            ("rig transform scale", self.scale),
            ("rig transform opacity", self.opacity),
        ):
            _finite_number(value, label)
        if self.scale <= 0:
            raise ProjectConfigError("rig transform scale must be greater than zero")
        if not 0 <= self.opacity <= 1:
            raise ProjectConfigError("rig transform opacity must be between zero and one")


@dataclass(frozen=True, slots=True)
class RigKeyframe:
    """A normalized pose sample with transforms keyed by part identifier."""

    at: float
    transforms: tuple[tuple[str, RigPartTransform], ...]

    def __post_init__(self) -> None:
        _finite_number(self.at, "rig keyframe at")
        if not 0 <= self.at <= 1:
            raise ProjectConfigError("rig keyframe at must be between zero and one")
        identifiers = tuple(part_id for part_id, _ in self.transforms)
        for part_id in identifiers:
            _required_string({"part_id": part_id}, "part_id")
        if len(identifiers) != len(set(identifiers)):
            raise ProjectConfigError("rig keyframe part identifiers must be unique")


@dataclass(frozen=True, slots=True)
class RigPose:
    """A named deterministic animation made from normalized keyframes."""

    pose_id: str
    keyframes: tuple[RigKeyframe, ...]
    duration_seconds: float = 1.0
    loop: bool = False

    def __post_init__(self) -> None:
        _required_string({"pose_id": self.pose_id}, "pose_id")
        _finite_number(self.duration_seconds, "rig pose duration_seconds", positive=True)
        if not isinstance(self.loop, bool):
            raise ProjectConfigError("rig pose loop must be a boolean")
        if len(self.keyframes) < 2:
            raise ProjectConfigError("rig pose requires at least two keyframes")
        points = tuple(keyframe.at for keyframe in self.keyframes)
        if points != tuple(sorted(set(points))):
            raise ProjectConfigError("rig pose keyframes must be strictly ordered")
        if points[0] != 0 or points[-1] != 1:
            raise ProjectConfigError("rig pose keyframes must start at zero and end at one")


@dataclass(frozen=True, slots=True)
class AssetRig:
    """A validated layered hierarchy and its reusable poses."""

    canvas_width: float
    canvas_height: float
    parts: tuple[RigPart, ...]
    poses: tuple[RigPose, ...]

    def __post_init__(self) -> None:
        _finite_number(self.canvas_width, "rig canvas_width", positive=True)
        _finite_number(self.canvas_height, "rig canvas_height", positive=True)
        if not self.parts:
            raise ProjectConfigError("rig requires at least one part")
        part_ids = tuple(part.part_id for part in self.parts)
        if len(part_ids) != len(set(part_ids)):
            raise ProjectConfigError("rig part identifiers must be unique")
        known_parts = set(part_ids)
        parents = {part.part_id: part.parent_id for part in self.parts}
        for part in self.parts:
            if part.parent_id is not None and part.parent_id not in known_parts:
                raise ProjectConfigError(
                    f"rig part {part.part_id} has unknown parent: {part.parent_id}"
                )
            current = part.part_id
            visited: set[str] = set()
            while parents[current] is not None:
                if current in visited:
                    raise ProjectConfigError("rig part hierarchy must not contain a cycle")
                visited.add(current)
                current = cast(str, parents[current])
        pose_ids = tuple(pose.pose_id for pose in self.poses)
        if len(pose_ids) != len(set(pose_ids)):
            raise ProjectConfigError("rig pose identifiers must be unique")
        for pose in self.poses:
            for keyframe in pose.keyframes:
                for part_id, _ in keyframe.transforms:
                    if part_id not in known_parts:
                        raise ProjectConfigError(
                            f"rig pose {pose.pose_id} references unknown part: {part_id}"
                        )


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
    animations: tuple[AssetAnimationCapability, ...] = ()
    rig: AssetRig | None = None

    def __post_init__(self) -> None:
        _required_string({"asset_id": self.asset_id}, "asset_id")
        if self.kind not in ASSET_KINDS:
            raise ProjectConfigError(f"asset kind must be one of: {', '.join(sorted(ASSET_KINDS))}")
        _validate_asset_path(self.path)
        if (self.animations or self.rig is not None) and self.kind not in {
            "character",
            "scene",
            "prop",
        }:
            raise ProjectConfigError("only visual assets can declare animation capabilities")
        animation_ids = tuple(animation.animation_id for animation in self.animations)
        if len(animation_ids) != len(set(animation_ids)):
            raise ProjectConfigError("asset animation identifiers must be unique")


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
            instances = {instance.instance_id: instance for instance in scene.instances}
            for animation in scene.animations:
                if animation.preset not in {"asset", "rig"}:
                    continue
                instance = instances[animation.target_instance_id]
                asset = asset_by_id[instance.asset_id]
                if animation.preset == "asset":
                    capability_ids = {capability.animation_id for capability in asset.animations}
                    if animation.asset_animation_id in capability_ids:
                        continue
                    raise ProjectConfigError(
                        f"asset {asset.asset_id} does not support animation: "
                        f"{animation.asset_animation_id}"
                    )
                pose_ids = {pose.pose_id for pose in asset.rig.poses} if asset.rig else set()
                if animation.rig_pose_id not in pose_ids:
                    raise ProjectConfigError(
                        f"asset {asset.asset_id} does not support rig pose: {animation.rig_pose_id}"
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
        capabilities = data.get("capabilities", {})
        if not isinstance(capabilities, dict):
            raise ProjectConfigError("asset capabilities must be an object")
        animations = capabilities.get("animations", [])
        if not isinstance(animations, list) or not all(
            isinstance(item, dict) for item in animations
        ):
            raise ProjectConfigError("asset capability animations must be a list of objects")
        rig_data = capabilities.get("rig")
        if rig_data is not None and not isinstance(rig_data, dict):
            raise ProjectConfigError("asset rig must be an object")
        return AssetConfig(
            asset_id=_required_string(data, "id"),
            kind=_required_string(data, "kind"),
            path=_required_string(data, "path"),
            animations=tuple(ProjectConfig._asset_animation_from_dict(item) for item in animations),
            rig=ProjectConfig._rig_from_dict(rig_data) if rig_data is not None else None,
        )

    @staticmethod
    def _asset_animation_from_dict(data: dict[str, Any]) -> AssetAnimationCapability:
        animation_type = _required_string(data, "type")
        frames = data.get("frames", [])
        if not isinstance(frames, list) or not all(isinstance(item, str) for item in frames):
            raise ProjectConfigError("frame-sequence frames must be a list of paths")
        return AssetAnimationCapability(
            animation_id=_required_string(data, "id"),
            animation_type=animation_type,
            fps=cast(float, data.get("fps")),
            loop=data.get("loop", True),
            path=data.get("path"),
            frames=tuple(frames),
            frame_width=data.get("frame_width"),
            frame_height=data.get("frame_height"),
            frame_count=data.get("frame_count"),
            columns=data.get("columns"),
        )

    @staticmethod
    def _rig_from_dict(data: dict[str, Any]) -> AssetRig:
        parts = ProjectConfig._list(data, "parts")
        poses = ProjectConfig._list(data, "poses")
        return AssetRig(
            canvas_width=cast(float, data.get("canvas_width")),
            canvas_height=cast(float, data.get("canvas_height")),
            parts=tuple(ProjectConfig._rig_part_from_dict(item) for item in parts),
            poses=tuple(ProjectConfig._rig_pose_from_dict(item) for item in poses),
        )

    @staticmethod
    def _rig_part_from_dict(data: dict[str, Any]) -> RigPart:
        return RigPart(
            part_id=_required_string(data, "id"),
            path=_required_string(data, "path"),
            x=cast(float, data.get("x", 0.0)),
            y=cast(float, data.get("y", 0.0)),
            width=cast(float, data.get("width")),
            height=cast(float, data.get("height")),
            pivot_x=cast(float, data.get("pivot_x", 0.0)),
            pivot_y=cast(float, data.get("pivot_y", 0.0)),
            parent_id=data.get("parent_id"),
            z_index=data.get("z_index", 0),
        )

    @staticmethod
    def _rig_pose_from_dict(data: dict[str, Any]) -> RigPose:
        keyframes = ProjectConfig._list(data, "keyframes")
        return RigPose(
            pose_id=_required_string(data, "id"),
            duration_seconds=cast(float, data.get("duration_seconds", 1.0)),
            loop=data.get("loop", False),
            keyframes=tuple(ProjectConfig._rig_keyframe_from_dict(item) for item in keyframes),
        )

    @staticmethod
    def _rig_keyframe_from_dict(data: dict[str, Any]) -> RigKeyframe:
        transforms = data.get("transforms", {})
        if not isinstance(transforms, dict) or not all(
            isinstance(part_id, str) and isinstance(value, dict)
            for part_id, value in transforms.items()
        ):
            raise ProjectConfigError("rig keyframe transforms must be an object")
        return RigKeyframe(
            at=cast(float, data.get("at")),
            transforms=tuple(
                (part_id, ProjectConfig._rig_transform_from_dict(value))
                for part_id, value in transforms.items()
            ),
        )

    @staticmethod
    def _rig_transform_from_dict(data: dict[str, Any]) -> RigPartTransform:
        return RigPartTransform(
            x=data.get("x", 0.0),
            y=data.get("y", 0.0),
            rotation=data.get("rotation", 0.0),
            scale=data.get("scale", 1.0),
            opacity=data.get("opacity", 1.0),
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
            asset_animation_id=data.get("asset_animation_id"),
            rig_pose_id=data.get("rig_pose_id"),
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
        resolved = {asset.asset_id: self.resolve_asset(asset) for asset in project.assets}
        for asset in project.assets:
            for animation in asset.animations:
                paths = (
                    (animation.path,)
                    if animation.animation_type == "sprite_sheet"
                    else animation.frames
                )
                for index, relative in enumerate(paths):
                    if relative is None:
                        continue
                    candidate = (self.asset_root / relative).resolve()
                    if not candidate.is_relative_to(self.asset_root):
                        raise AssetResolutionError(
                            f"animation asset path escapes asset root: {relative}"
                        )
                    if not candidate.is_file():
                        raise AssetResolutionError(f"animation asset file not found: {relative}")
                    if candidate.suffix.lower() not in IMAGE_EXTENSIONS:
                        raise AssetResolutionError(
                            f"animation asset has incompatible extension: {relative}"
                        )
                    resolved[
                        capability_asset_key(asset.asset_id, animation.animation_id, index)
                    ] = candidate
            if asset.rig is not None:
                for part in asset.rig.parts:
                    candidate = (self.asset_root / part.path).resolve()
                    if not candidate.is_relative_to(self.asset_root):
                        raise AssetResolutionError(f"rig part path escapes asset root: {part.path}")
                    if not candidate.is_file():
                        raise AssetResolutionError(f"rig part file not found: {part.path}")
                    if candidate.suffix.lower() not in IMAGE_EXTENSIONS:
                        raise AssetResolutionError(
                            f"rig part has incompatible extension: {part.path}"
                        )
                    resolved[rig_part_asset_key(asset.asset_id, part.part_id)] = candidate
        return resolved
