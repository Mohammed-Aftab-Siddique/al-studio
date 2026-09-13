"""Validated, provider-neutral script configuration models."""

from dataclasses import dataclass
from typing import Any


SCRIPT_SCHEMA_VERSION = 1
EVENT_TYPES = frozenset({"dialogue", "action", "ambience", "sound_effect", "caption"})


def _validate_string(field_name: str, value: Any) -> str:
    if not isinstance(value, str) or not value.strip() or value != value.strip():
        raise ValueError(f"{field_name} must be a non-empty trimmed string")
    return value


def _validate_duration(value: Any) -> float:
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
        raise ValueError("duration_seconds must be a positive number")
    return float(value)


@dataclass(frozen=True, slots=True)
class ScriptEvent:
    """A timed non-dialogue instruction in a scene."""

    event_type: str
    duration_seconds: float
    payload: dict[str, Any]

    def __post_init__(self) -> None:
        if self.event_type not in EVENT_TYPES - {"dialogue"}:
            raise ValueError(f"unsupported non-dialogue event type: {self.event_type}")
        _validate_duration(self.duration_seconds)
        if not isinstance(self.payload, dict):
            raise TypeError("event payload must be an object")


@dataclass(frozen=True, slots=True)
class DialogueEvent:
    """Dialogue that is timed from generated speech rather than a fixed duration."""

    speaker: str
    text: str
    caption: str | None = None

    def __post_init__(self) -> None:
        _validate_string("speaker", self.speaker)
        _validate_string("text", self.text)
        if self.caption is not None:
            _validate_string("caption", self.caption)


@dataclass(frozen=True, slots=True)
class ScriptScene:
    scene_id: str
    events: tuple[DialogueEvent | ScriptEvent, ...]

    def __post_init__(self) -> None:
        _validate_string("scene_id", self.scene_id)
        if not isinstance(self.events, tuple):
            raise TypeError("events must be a tuple")


@dataclass(frozen=True, slots=True)
class ScriptConfig:
    scenes: tuple[ScriptScene, ...]
    schema_version: int = SCRIPT_SCHEMA_VERSION

    def __post_init__(self) -> None:
        if self.schema_version != SCRIPT_SCHEMA_VERSION:
            raise ValueError(f"unsupported script schema version: {self.schema_version}")
        if not isinstance(self.scenes, tuple) or not self.scenes:
            raise ValueError("script must contain at least one scene")
        scene_ids = tuple(scene.scene_id for scene in self.scenes)
        if len(scene_ids) != len(set(scene_ids)):
            raise ValueError("script scene identifiers must be unique")
