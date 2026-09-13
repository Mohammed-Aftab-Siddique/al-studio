from pathlib import Path

import pytest

from app.script import DialogueEvent, ScriptConfigError, ScriptEvent, load_script
from app.script.parser import parse_script


SCRIPT_PATH = Path("projects/starter-project/script.json")


def test_starter_script_loads_documented_event_types() -> None:
    script = load_script(SCRIPT_PATH)

    assert script.schema_version == 1
    assert script.scenes[0].scene_id == "starter-room"
    assert isinstance(script.scenes[0].events[0], DialogueEvent)
    assert isinstance(script.scenes[0].events[1], ScriptEvent)
    assert script.scenes[0].events[1].event_type == "action"


@pytest.mark.parametrize(
    "raw, message",
    [
        ({"schema_version": 2, "scenes": []}, "unsupported script schema version: 2"),
        ({"schema_version": 1, "scenes": "no"}, "scenes must be a list"),
        (
            {"schema_version": 1, "scenes": [{"scene_id": "room", "events": [{"type": "unknown"}]}]},
            "unsupported event type: unknown",
        ),
        (
            {"schema_version": 1, "scenes": [{"scene_id": "room", "events": [{"type": "action", "duration_seconds": 0}]}]},
            "duration_seconds must be a positive number",
        ),
    ],
)
def test_script_parser_reports_invalid_schema_clearly(raw: dict, message: str) -> None:
    with pytest.raises(ScriptConfigError, match=message):
        parse_script(raw)


def test_script_requires_at_least_one_scene() -> None:
    with pytest.raises(ScriptConfigError, match="script must contain at least one scene"):
        parse_script({"schema_version": 1, "scenes": []})


def test_script_loader_reports_invalid_json(tmp_path: Path) -> None:
    path = tmp_path / "script.json"
    path.write_text("{", encoding="utf-8")

    with pytest.raises(ScriptConfigError, match="invalid JSON"):
        load_script(path)
