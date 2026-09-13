from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.animation import CharacterState, FrameRenderer
from app.audio.voice import VoiceEngine
from app.project import ProjectAssetManager
from app.script import DialogueTimelineBuilder, load_script


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
