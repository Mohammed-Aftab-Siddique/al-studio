"""Dialogue synthesis and deterministic scene timeline construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import soundfile as sf

from app.audio.voice import VoiceEngine
from app.project import ProjectConfig, ProjectConfigError

from .model import DialogueEvent, ScriptConfig, ScriptEvent


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """A concrete event consumed by animation, audio, and caption stages."""

    event_id: str
    event_type: str
    scene_id: str
    start_seconds: float
    duration_seconds: float
    payload: dict[str, Any]


class DialogueTimelineBuilder:
    """Build a sequential timeline and synthesize dialogue through VoiceEngine."""

    def __init__(self, voice_engine: VoiceEngine) -> None:
        self.voice_engine = voice_engine

    def build(
        self,
        project: ProjectConfig,
        script: ScriptConfig,
        output_dir: Path,
    ) -> tuple[TimelineEvent, ...]:
        characters = {character.name: character for character in project.characters}
        project_scene_ids = {scene.scene_id for scene in project.scenes}
        output_dir.mkdir(parents=True, exist_ok=True)
        timeline: list[TimelineEvent] = []
        current_time = 0.0

        for scene in script.scenes:
            if scene.scene_id not in project_scene_ids:
                raise ProjectConfigError(f"script references unknown scene: {scene.scene_id}")
            for event_index, event in enumerate(scene.events):
                event_id = f"{scene.scene_id}-{event_index:03d}"
                if isinstance(event, DialogueEvent):
                    character = characters.get(event.speaker)
                    if character is None:
                        raise ProjectConfigError(
                            f"script references unknown speaker: {event.speaker}"
                        )
                    output_path = output_dir / "dialogue" / f"{event_id}.wav"
                    self.voice_engine.synthesize(event.text, character.voice_id, output_path)
                    duration = float(sf.info(output_path).duration)
                    if duration <= 0:
                        raise ProjectConfigError(f"generated dialogue has no duration: {event_id}")
                    payload = {
                        "speaker": event.speaker,
                        "text": event.text,
                        "caption": event.caption or event.text,
                        "audio_path": str(output_path),
                    }
                    timeline_event = TimelineEvent(
                        event_id=event_id,
                        event_type="dialogue",
                        scene_id=scene.scene_id,
                        start_seconds=current_time,
                        duration_seconds=duration,
                        payload=payload,
                    )
                else:
                    timeline_event = self._timed_event(
                        event_id, scene.scene_id, current_time, event
                    )
                timeline.append(timeline_event)
                current_time += timeline_event.duration_seconds
        return tuple(timeline)

    @staticmethod
    def _timed_event(
        event_id: str,
        scene_id: str,
        start_seconds: float,
        event: ScriptEvent,
    ) -> TimelineEvent:
        return TimelineEvent(
            event_id=event_id,
            event_type=event.event_type,
            scene_id=scene_id,
            start_seconds=start_seconds,
            duration_seconds=event.duration_seconds,
            payload=event.payload,
        )
