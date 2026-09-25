from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.animation import CharacterState, FrameRenderer
from app.audio.voice import VoiceEngine
from app.project import ProjectAssetManager, ProjectConfig
from app.scenes import SceneAnimation
from app.script import DialogueTimelineBuilder, TimelineEvent, load_script


class FakeVoiceEngine(VoiceEngine):
    def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, np.zeros(2400, dtype=np.float32), 24000)
        return output_path


def _renderer_and_timeline(tmp_path: Path):
    manager = ProjectAssetManager(Path("assets"))
    project = manager.load_project(Path("projects/starter-project/project.json"))
    timeline = DialogueTimelineBuilder(FakeVoiceEngine()).build(
        project, load_script(Path("projects/starter-project/script.json")), tmp_path / "audio"
    )
    return FrameRenderer(project, manager.validate_assets(project)), timeline


def test_frame_renderer_embeds_reusable_scene_and_character_assets(tmp_path: Path) -> None:
    renderer, timeline = _renderer_and_timeline(tmp_path)

    frame = renderer.render_frame(timeline, 0.0, tmp_path / "frame.svg")

    contents = frame.path.read_text(encoding="utf-8")
    assert frame.scene_id == "starter-room"
    assert frame.mouth_open is True
    assert contents.count("data:image/svg+xml;base64,") == 3
    assert 'data-mouth="open"' in contents


def test_dialogue_mouth_state_is_timed_and_deterministic(tmp_path: Path) -> None:
    renderer, timeline = _renderer_and_timeline(tmp_path)

    open_frame = renderer.render_frame(timeline, 0.0, tmp_path / "open.svg")
    closed_frame = renderer.render_frame(timeline, 0.09, tmp_path / "closed.svg")

    assert open_frame.mouth_open is True
    assert closed_frame.mouth_open is False
    assert 'data-mouth="closed"' in closed_frame.path.read_text(encoding="utf-8")


def test_frame_renderer_generates_expected_sequence_length(tmp_path: Path) -> None:
    renderer, timeline = _renderer_and_timeline(tmp_path)

    frames = renderer.render_sequence(timeline, tmp_path / "frames", fps=10)

    assert len(frames) == 24
    assert frames[0].path.name == "frame-000000.svg"
    assert frames[-1].path.is_file()


def test_character_state_validates_core_rig_properties() -> None:
    with pytest.raises(ValueError, match="facing must be left or right"):
        CharacterState(facing="up")
    with pytest.raises(ValueError, match="scale must be greater than zero"):
        CharacterState(scale=0)


def test_frame_renderer_honors_instance_transform_layer_and_character_placement(
    tmp_path: Path,
) -> None:
    for relative in ("scenes/room.svg", "characters/hero.svg", "props/cat.svg"):
        path = tmp_path / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<svg xmlns='http://www.w3.org/2000/svg'/>", encoding="utf-8")
    project = ProjectConfig.from_dict(
        {
            "schema_version": 1,
            "name": "composed",
            "assets": [
                {"id": "room", "kind": "scene", "path": "scenes/room.svg"},
                {"id": "hero", "kind": "character", "path": "characters/hero.svg"},
                {"id": "cat", "kind": "prop", "path": "props/cat.svg"},
            ],
            "characters": [{"name": "Alex", "voice_id": "am_adam", "visual_asset_id": "hero"}],
            "scenes": [
                {
                    "id": "room",
                    "background_asset_id": "room",
                    "instances": [
                        {
                            "id": "hero-left",
                            "asset_id": "hero",
                            "x": 80,
                            "y": 170,
                            "width": 300,
                            "height": 500,
                            "rotation": -5,
                            "z_index": 2,
                        },
                        {
                            "id": "cat-right",
                            "asset_id": "cat",
                            "x": 900,
                            "y": 470,
                            "width": 220,
                            "height": 180,
                            "opacity": 0.8,
                            "z_index": 5,
                        },
                    ],
                }
            ],
        }
    )
    assets = ProjectAssetManager(tmp_path).validate_assets(project)
    timeline = (TimelineEvent("room-000", "dialogue", "room", 0, 1, {"speaker": "Alex"}),)

    frame = FrameRenderer(project, assets).render_frame(timeline, 0, tmp_path / "frame.svg")
    contents = frame.path.read_text(encoding="utf-8")

    assert 'transform="translate(80 170) rotate(-5 150.0 250.0)"' in contents
    assert 'data-instance="hero-left"' in contents
    assert 'data-instance="cat-right"' in contents
    assert 'opacity="0.8"' in contents
    assert contents.index('data-instance="hero-left"') < contents.index('data-instance="cat-right"')

    animation = SceneAnimation("hero-enter", "hero-left", "slide-in", 0, 1, "linear", "left", False)
    animated_scene = replace(project.scenes[0], animations=(animation,))
    animated_project = replace(project, scenes=(animated_scene,))
    animated_frame = FrameRenderer(animated_project, assets).render_frame(
        timeline, 0.5, tmp_path / "animated.svg"
    )
    animated_contents = animated_frame.path.read_text(encoding="utf-8")

    assert 'data-instance="hero-left"' in animated_contents
    assert 'transform="translate(-10.0 170.0)' in animated_contents
