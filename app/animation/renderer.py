"""Dependency-free SVG frame renderer for the first 2D animation slice."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from html import escape
from pathlib import Path

from app.project import ProjectConfig
from app.script.timeline import TimelineEvent


@dataclass(frozen=True, slots=True)
class CharacterState:
    """Reusable deterministic character rig state."""

    x: float = 420.0
    y: float = 200.0
    scale: float = 1.0
    facing: str = "right"
    visible: bool = True
    expression: str = "neutral"

    def __post_init__(self) -> None:
        if self.scale <= 0:
            raise ValueError("character scale must be greater than zero")
        if self.facing not in {"left", "right"}:
            raise ValueError("character facing must be left or right")
        if not isinstance(self.visible, bool):
            raise TypeError("character visible must be a boolean")


@dataclass(frozen=True, slots=True)
class RenderedFrame:
    path: Path
    scene_id: str
    time_seconds: float
    mouth_open: bool


class FrameRenderer:
    """Renders scene SVG frames from assets, timeline events, and rig state."""

    def __init__(self, project: ProjectConfig, asset_paths: dict[str, Path]) -> None:
        self.project = project
        self.asset_paths = asset_paths
        self.scenes = {scene.scene_id: scene for scene in project.scenes}
        self.characters = {character.name: character for character in project.characters}

    def render_frame(
        self,
        timeline: tuple[TimelineEvent, ...],
        time_seconds: float,
        output_path: Path,
        character_state: CharacterState = CharacterState(),
    ) -> RenderedFrame:
        event = self._event_at(timeline, time_seconds)
        scene = self.scenes[event.scene_id]
        background = self._image(self.asset_paths[scene.background_asset_id], 0, 0, 1280, 720)
        props = "".join(
            self._image(self.asset_paths[prop_id], 1030 + index * 55, 405, 140, 205)
            for index, prop_id in enumerate(scene.prop_asset_ids)
        )
        character_svg, mouth_open = self._character_svg(event, time_seconds, character_state)
        camera = scene.camera
        content = (
            f'<g transform="translate({camera.x} {camera.y}) scale({camera.zoom})">'
            f"{background}{props}{character_svg}</g>"
        )
        svg = (
            '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" '
            'viewBox="0 0 1280 720" role="img">'
            f"<title>AL Studio frame at {time_seconds:.3f} seconds</title>{content}</svg>"
        )
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(svg, encoding="utf-8")
        return RenderedFrame(output_path, scene.scene_id, time_seconds, mouth_open)

    def render_sequence(
        self,
        timeline: tuple[TimelineEvent, ...],
        output_dir: Path,
        fps: int | None = None,
    ) -> tuple[RenderedFrame, ...]:
        if not timeline:
            return ()
        frame_rate = fps or self.project.render.fps
        duration = timeline[-1].start_seconds + timeline[-1].duration_seconds
        frame_count = max(1, round(duration * frame_rate))
        return tuple(
            self.render_frame(timeline, index / frame_rate, output_dir / f"frame-{index:06d}.svg")
            for index in range(frame_count)
        )

    @staticmethod
    def _event_at(timeline: tuple[TimelineEvent, ...], time_seconds: float) -> TimelineEvent:
        if time_seconds < 0:
            raise ValueError("frame time must not be negative")
        for event in timeline:
            if event.start_seconds <= time_seconds < event.start_seconds + event.duration_seconds:
                return event
        return timeline[-1]

    def _character_svg(
        self,
        event: TimelineEvent,
        time_seconds: float,
        state: CharacterState,
    ) -> tuple[str, bool]:
        if event.event_type != "dialogue" or not state.visible:
            return "", False
        character = self.characters[event.payload["speaker"]]
        if character.visual_asset_id is None:
            return "", False
        scale_x = -state.scale if state.facing == "left" else state.scale
        mouth_open = int((time_seconds - event.start_seconds) * 12) % 2 == 0
        mouth_height = 18 if mouth_open else 5
        image = self._image(self.asset_paths[character.visual_asset_id], 0, 0, 320, 480)
        mouth = (
            f'<ellipse cx="160" cy="204" rx="28" ry="{mouth_height}" '
            'fill="#8a3d4b" data-mouth="open"/>'
            if mouth_open
            else '<path d="M132 204h56" stroke="#8a3d4b" stroke-width="6" '
            'stroke-linecap="round" data-mouth="closed"/>'
        )
        transform = f"translate({state.x} {state.y}) scale({scale_x} {state.scale})"
        return f'<g transform="{transform}" data-expression="{escape(state.expression)}">{image}{mouth}</g>', mouth_open

    @staticmethod
    def _image(path: Path, x: float, y: float, width: float, height: float) -> str:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        mime_type = "image/svg+xml" if path.suffix.lower() == ".svg" else "image/png"
        return f'<image href="data:{mime_type};base64,{encoded}" x="{x}" y="{y}" width="{width}" height="{height}"/>'
