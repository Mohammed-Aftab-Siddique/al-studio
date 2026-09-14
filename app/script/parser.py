"""JSON parser for the documented AL Studio script format."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from .model import SCRIPT_SCHEMA_VERSION, DialogueEvent, ScriptConfig, ScriptEvent, ScriptScene


class ScriptConfigError(ValueError):
    """Raised for malformed or unsupported script configuration."""


def load_script(script_path: Path) -> ScriptConfig:
    """Load and validate a versioned script JSON file."""
    try:
        raw = json.loads(script_path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise ScriptConfigError(f"script file not found: {script_path}") from error
    except json.JSONDecodeError as error:
        raise ScriptConfigError(f"invalid JSON in script file: {script_path}") from error
    return parse_script(raw)


def parse_script(raw: Any) -> ScriptConfig:
    if not isinstance(raw, dict):
        raise ScriptConfigError("script configuration must be an object")
    if raw.get("schema_version") != SCRIPT_SCHEMA_VERSION:
        raise ScriptConfigError(f"unsupported script schema version: {raw.get('schema_version')}")
    scenes = raw.get("scenes")
    if not isinstance(scenes, list):
        raise ScriptConfigError("scenes must be a list")
    try:
        return ScriptConfig(scenes=tuple(_parse_scene(scene) for scene in scenes))
    except (TypeError, ValueError) as error:
        raise ScriptConfigError(str(error)) from error


def _parse_scene(raw: Any) -> ScriptScene:
    if not isinstance(raw, dict):
        raise ScriptConfigError("scene must be an object")
    events = raw.get("events")
    if not isinstance(events, list):
        raise ScriptConfigError("scene events must be a list")
    return ScriptScene(
        scene_id=cast(str, raw.get("scene_id")),
        events=tuple(_parse_event(event) for event in events),
    )


def _parse_event(raw: Any) -> DialogueEvent | ScriptEvent:
    if not isinstance(raw, dict):
        raise ScriptConfigError("event must be an object")
    event_type = raw.get("type")
    if event_type == "dialogue":
        return DialogueEvent(
            speaker=cast(str, raw.get("speaker")),
            text=cast(str, raw.get("text")),
            caption=raw.get("caption"),
        )
    if event_type not in {"action", "ambience", "sound_effect", "caption"}:
        raise ScriptConfigError(f"unsupported event type: {event_type}")
    payload = {key: value for key, value in raw.items() if key not in {"type", "duration_seconds"}}
    return ScriptEvent(
        event_type=event_type,
        duration_seconds=cast(float, raw.get("duration_seconds")),
        payload=payload,
    )
