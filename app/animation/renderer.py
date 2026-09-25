"""Dependency-free SVG frame renderer for the first 2D animation slice."""

from __future__ import annotations

import base64
from dataclasses import dataclass
from html import escape
from pathlib import Path

from app.project import ProjectConfig
from app.scenes import SceneInstance
from app.script.timeline import TimelineEvent

from .presets import AnimationTransform, evaluate_animations


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


DEFAULT_CHARACTER_STATE = CharacterState()


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
        character_state: CharacterState = DEFAULT_CHARACTER_STATE,
    ) -> RenderedFrame:
        event = self._event_at(timeline, time_seconds)
        scene = self.scenes[event.scene_id]
        scene_start = next(
            item.start_seconds for item in timeline if item.scene_id == scene.scene_id
        )
        scene_time = max(0.0, time_seconds - scene_start)
        background = self._image(self.asset_paths[scene.background_asset_id], 0, 0, 1280, 720)
        legacy_props = "".join(
            self._image(self.asset_paths[prop_id], 1030 + index * 55, 405, 140, 205)
            for index, prop_id in enumerate(scene.prop_asset_ids)
        )
        character_instance = self._speaking_character_instance(event, scene.instances)
        character_animation = (
            evaluate_animations(character_instance.instance_id, scene.animations, scene_time)
            if character_instance
            else AnimationTransform()
        )
        character_svg, mouth_open = self._character_svg(
            event, time_seconds, character_state, character_instance, character_animation
        )
        instances = "".join(
            character_svg
            if character_instance is not None
            and instance.instance_id == character_instance.instance_id
            else self._instance_svg(
                instance, evaluate_animations(instance.instance_id, scene.animations, scene_time)
            )
            for instance in sorted(
                scene.instances, key=lambda item: (item.z_index, item.instance_id)
            )
            if instance.visible
        )
        fallback_character = character_svg if character_instance is None else ""
        camera = scene.camera
        content = (
            f'<g transform="translate({camera.x} {camera.y}) scale({camera.zoom})">'
            f"{background}{legacy_props}{instances}{fallback_character}</g>"
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
        instance: SceneInstance | None,
        animation: AnimationTransform,
    ) -> tuple[str, bool]:
        if event.event_type != "dialogue" or not state.visible:
            return "", False
        character = self.characters[event.payload["speaker"]]
        if character.visual_asset_id is None:
            return "", False
        mouth_open = int((time_seconds - event.start_seconds) * 12) % 2 == 0
        width = instance.width if instance else 320
        height = instance.height if instance else 480
        mouth_height = height * (0.0375 if mouth_open else 0.0104)
        image = self._image(self.asset_paths[character.visual_asset_id], 0, 0, width, height)
        mouth = (
            f'<ellipse cx="{width / 2}" cy="{height * 0.425}" '
            f'rx="{width * 0.0875}" ry="{mouth_height}" '
            'fill="#8a3d4b" data-mouth="open"/>'
            if mouth_open
            else f'<path d="M{width * 0.4125} {height * 0.425}h{width * 0.175}" '
            f' stroke="#8a3d4b" stroke-width="{max(2, width * 0.01875)}" '
            'stroke-linecap="round" data-mouth="closed"/>'
        )
        if instance:
            transform = self._instance_transform(instance, animation)
            opacity = instance.opacity * animation.opacity
            instance_attribute = f' data-instance="{escape(instance.instance_id)}"'
        else:
            scale_x = -state.scale if state.facing == "left" else state.scale
            transform = f"translate({state.x} {state.y}) scale({scale_x} {state.scale})"
            opacity = 1
            instance_attribute = ""
        return (
            (
                f'<g transform="{transform}" opacity="{opacity}"{instance_attribute} '
                f'data-expression="{escape(state.expression)}">{image}{mouth}</g>'
            ),
            mouth_open,
        )

    def _instance_svg(self, instance: SceneInstance, animation: AnimationTransform) -> str:
        image = self._image(
            self.asset_paths[instance.asset_id], 0, 0, instance.width, instance.height
        )
        transform = self._instance_transform(instance, animation)
        return (
            f'<g transform="{transform}" opacity="{instance.opacity * animation.opacity}" '
            f'data-instance="{escape(instance.instance_id)}">{image}</g>'
        )

    @staticmethod
    def _instance_transform(instance: SceneInstance, animation: AnimationTransform) -> str:
        center_x = instance.width / 2
        center_y = instance.height / 2
        if animation == AnimationTransform():
            return (
                f"translate({instance.x} {instance.y}) "
                f"rotate({instance.rotation} {center_x} {center_y})"
            )
        transform = (
            f"translate({instance.x + animation.x} {instance.y + animation.y}) "
            f"rotate({instance.rotation + animation.rotation} {center_x} {center_y})"
        )
        if animation.scale != 1:
            transform += (
                f" translate({center_x} {center_y}) scale({animation.scale})"
                f" translate({-center_x} {-center_y})"
            )
        return transform

    def _speaking_character_instance(
        self,
        event: TimelineEvent,
        instances: tuple[SceneInstance, ...],
    ) -> SceneInstance | None:
        if event.event_type != "dialogue":
            return None
        character = self.characters[event.payload["speaker"]]
        if character.visual_asset_id is None:
            return None
        return next(
            (
                instance
                for instance in instances
                if instance.asset_id == character.visual_asset_id and instance.visible
            ),
            None,
        )

    @staticmethod
    def _image(path: Path, x: float, y: float, width: float, height: float) -> str:
        encoded = base64.b64encode(path.read_bytes()).decode("ascii")
        mime_type = {
            ".svg": "image/svg+xml",
            ".png": "image/png",
            ".webp": "image/webp",
        }[path.suffix.lower()]
        return f'<image href="data:{mime_type};base64,{encoded}" x="{x}" y="{y}" width="{width}" height="{height}"/>'
