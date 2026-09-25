"""Dialogue synthesis and deterministic scene timeline construction."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import soundfile as sf

from app.audio.voice import VoiceEngine
from app.project import ProjectConfig, ProjectConfigError

from .model import DialogueEvent, ScriptConfig, ScriptEvent


def validate_script_references(project: ProjectConfig, script: ScriptConfig) -> None:
    """Validate every cross-file scene, speaker, and audio reference without rendering."""
    scenes = {scene.scene_id for scene in project.scenes}
    speakers = {character.name for character in project.characters}
    assets = {asset.asset_id: asset for asset in project.assets}
    for scene in script.scenes:
        if scene.scene_id not in scenes:
            raise ProjectConfigError(f"script references unknown scene: {scene.scene_id}")
        for event in scene.events:
            if isinstance(event, DialogueEvent) and event.speaker not in speakers:
                raise ProjectConfigError(f"script references unknown speaker: {event.speaker}")
            if isinstance(event, ScriptEvent) and event.event_type in {
                "ambience",
                "sound_effect",
            }:
                asset_id = event.payload.get("asset_id")
                if not isinstance(asset_id, str) or not asset_id:
                    raise ProjectConfigError("audio event requires an asset_id")
                asset = assets.get(asset_id)
                if asset is None:
                    raise ProjectConfigError(f"script references unknown audio asset: {asset_id}")
                if asset.kind not in {"audio", "music"}:
                    raise ProjectConfigError(f"asset {asset_id} is not an audio asset")


@dataclass(frozen=True, slots=True)
class TimelineEvent:
    """A concrete event consumed by animation, audio, and caption stages."""

    event_id: str
    event_type: str
    scene_id: str
    start_seconds: float
    duration_seconds: float
    payload: dict[str, Any]
    track: str = "visual"
    scene_start_seconds: float = 0.0
    scene_duration_seconds: float = 0.0


class DialogueTimelineBuilder:
    """Build parallel scene tracks and synthesize dialogue through VoiceEngine."""

    def __init__(self, voice_engine: VoiceEngine) -> None:
        self.voice_engine = voice_engine

    def build(
        self,
        project: ProjectConfig,
        script: ScriptConfig,
        output_dir: Path,
        asset_paths: dict[str, Path] | None = None,
    ) -> tuple[TimelineEvent, ...]:
        validate_script_references(project, script)
        characters = {character.name: character for character in project.characters}
        project_scenes = {scene.scene_id: scene for scene in project.scenes}
        project_assets = {asset.asset_id: asset for asset in project.assets}
        output_dir.mkdir(parents=True, exist_ok=True)
        timeline: list[TimelineEvent] = []
        scene_offset = 0.0

        for scene in script.scenes:
            project_scene = project_scenes.get(scene.scene_id)
            if project_scene is None:
                raise ProjectConfigError(f"script references unknown scene: {scene.scene_id}")
            scene_events: list[TimelineEvent] = []
            sequential_cursor = 0.0
            for event_index, event in enumerate(scene.events):
                event_id = f"{scene.scene_id}-{event_index:03d}"
                local_start = event.start_seconds
                if local_start is None:
                    local_start = sequential_cursor
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
                        start_seconds=local_start,
                        duration_seconds=duration,
                        payload=payload,
                        track="dialogue",
                    )
                else:
                    timeline_event = self._timed_event(
                        event_id,
                        scene.scene_id,
                        local_start,
                        event,
                        project_assets,
                        asset_paths,
                    )
                scene_events.append(timeline_event)
                sequential_cursor = max(
                    sequential_cursor,
                    local_start + timeline_event.duration_seconds,
                )

            for animation in project_scene.animations:
                scene_events.append(
                    TimelineEvent(
                        event_id=f"{scene.scene_id}-animation-{animation.animation_id}",
                        event_type="animation",
                        scene_id=scene.scene_id,
                        start_seconds=animation.start_seconds,
                        duration_seconds=animation.duration_seconds,
                        payload={
                            "animation_id": animation.animation_id,
                            "target": animation.target_instance_id,
                            "preset": animation.preset,
                            "loop": animation.loop,
                        },
                        track="visual",
                    )
                )

            if not scene_events:
                scene_events.append(
                    TimelineEvent(
                        event_id=f"{scene.scene_id}-hold",
                        event_type="scene_hold",
                        scene_id=scene.scene_id,
                        start_seconds=0.0,
                        duration_seconds=1.0,
                        payload={},
                        track="visual",
                    )
                )
            scene_duration = max(
                item.start_seconds + item.duration_seconds for item in scene_events
            )
            timeline.extend(
                TimelineEvent(
                    event_id=item.event_id,
                    event_type=item.event_type,
                    scene_id=item.scene_id,
                    start_seconds=scene_offset + item.start_seconds,
                    duration_seconds=item.duration_seconds,
                    payload=item.payload,
                    track=item.track,
                    scene_start_seconds=scene_offset,
                    scene_duration_seconds=scene_duration,
                )
                for item in scene_events
            )
            scene_offset += scene_duration
        track_order = {"visual": 0, "dialogue": 1, "caption": 2, "audio": 3}
        return tuple(
            sorted(
                timeline,
                key=lambda item: (
                    item.start_seconds,
                    track_order.get(item.track, 9),
                    item.event_id,
                ),
            )
        )

    @staticmethod
    def _timed_event(
        event_id: str,
        scene_id: str,
        start_seconds: float,
        event: ScriptEvent,
        project_assets: dict[str, Any],
        asset_paths: dict[str, Path] | None,
    ) -> TimelineEvent:
        track = {
            "action": "visual",
            "caption": "caption",
            "ambience": "audio",
            "sound_effect": "audio",
        }[event.event_type]
        payload = dict(event.payload)
        if event.event_type in {"ambience", "sound_effect"}:
            asset_id = payload.get("asset_id")
            if not isinstance(asset_id, str) or not asset_id:
                raise ProjectConfigError("audio event requires an asset_id")
            asset = project_assets.get(asset_id)
            if asset is None:
                raise ProjectConfigError(f"script references unknown audio asset: {asset_id}")
            if asset.kind not in {"audio", "music"}:
                raise ProjectConfigError(f"asset {asset_id} is not an audio asset")
            if asset_paths is not None:
                payload["audio_path"] = str(asset_paths[asset_id])
        return TimelineEvent(
            event_id=event_id,
            event_type=event.event_type,
            scene_id=scene_id,
            start_seconds=start_seconds,
            duration_seconds=event.duration_seconds,
            payload=payload,
            track=track,
        )
