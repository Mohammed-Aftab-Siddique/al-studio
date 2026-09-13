from pathlib import Path

import numpy as np
import pytest
import soundfile as sf

from app.audio.voice import VoiceEngine
from app.project import ProjectAssetManager, ProjectConfigError
from app.script import DialogueTimelineBuilder, load_script
from app.script.parser import parse_script


class FakeVoiceEngine(VoiceEngine):
    def __init__(self) -> None:
        self.calls: list[tuple[str, str, Path]] = []

    def synthesize(self, text: str, voice: str, output_path: Path) -> Path:
        self.validate_synthesis_request(text, voice, output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        sf.write(output_path, np.zeros(2400, dtype=np.float32), 24000)
        self.calls.append((text, voice, output_path))
        return output_path


def _starter_project():
    return ProjectAssetManager(Path("assets")).load_project(Path("projects/starter-project/project.json"))


def test_timeline_synthesizes_dialogue_and_uses_measured_duration(tmp_path: Path) -> None:
    voice_engine = FakeVoiceEngine()
    script = load_script(Path("projects/starter-project/script.json"))

    timeline = DialogueTimelineBuilder(voice_engine).build(_starter_project(), script, tmp_path)

    dialogue, action, caption = timeline
    assert voice_engine.calls[0][0:2] == ("Welcome to AL Studio. Let's make a story.", "am_adam")
    assert dialogue.event_type == "dialogue"
    assert dialogue.duration_seconds == pytest.approx(0.1)
    assert dialogue.payload["caption"] == "Welcome to AL Studio. Let's make a story."
    assert action.start_seconds == pytest.approx(0.1)
    assert caption.start_seconds == pytest.approx(0.9)
    assert Path(dialogue.payload["audio_path"]).is_file()


def test_timeline_rejects_unknown_speaker_before_synthesis(tmp_path: Path) -> None:
    script = parse_script(
        {
            "schema_version": 1,
            "scenes": [{"scene_id": "starter-room", "events": [{"type": "dialogue", "speaker": "Missing", "text": "Hi"}]}],
        }
    )
    voice_engine = FakeVoiceEngine()

    with pytest.raises(ProjectConfigError, match="unknown speaker: Missing"):
        DialogueTimelineBuilder(voice_engine).build(_starter_project(), script, tmp_path)

    assert voice_engine.calls == []


def test_timeline_rejects_unknown_scene_before_synthesis(tmp_path: Path) -> None:
    script = parse_script(
        {
            "schema_version": 1,
            "scenes": [{"scene_id": "missing", "events": [{"type": "dialogue", "speaker": "Alex", "text": "Hi"}]}],
        }
    )

    with pytest.raises(ProjectConfigError, match="unknown scene: missing"):
        DialogueTimelineBuilder(FakeVoiceEngine()).build(_starter_project(), script, tmp_path)
