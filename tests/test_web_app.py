import asyncio
import json
from pathlib import Path

import httpx

from app.pipeline import RenderResult
from app.web.app import create_app


class FakeVoiceEngine:
    def synthesize(self, text: str, voice: str, output: Path) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_bytes(b"RIFF\x00\x00\x00\x00WAVE")
        return output


class FakePipeline:
    def __init__(self, asset_root: Path) -> None:
        self.asset_root = asset_root

    def render(
        self, project: Path, script: Path, output: Path, dry_run: bool, progress
    ) -> RenderResult:
        progress("validating", 5)
        output.mkdir(parents=True, exist_ok=True)
        (output / "metadata.json").write_text(
            json.dumps({"status": "dry-run" if dry_run else "complete"}), encoding="utf-8"
        )
        video = None
        if not dry_run:
            progress("compositing video", 85)
            video = output / "final" / "demo.mp4"
            video.parent.mkdir(parents=True)
            video.write_bytes(b"video")
        progress("complete", 100)
        return RenderResult(output, video, dry_run)


def call(app, method: str, path: str, **kwargs: object) -> httpx.Response:
    async def request() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
            return await client.request(method, path, **kwargs)

    return asyncio.run(request())


def make_app(tmp_path: Path):
    return create_app(tmp_path, pipeline_factory=FakePipeline, voice_engine_factory=FakeVoiceEngine)


def create_demo(app) -> dict:
    response = call(app, "POST", "/api/projects", json={"name": "Demo Story"})
    assert response.status_code == 201
    return response.json()


def test_web_shell_and_static_assets_are_available(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    assert call(app, "GET", "/api/health").json() == {"status": "ready", "scope": "local-only"}
    home = call(app, "GET", "/")
    script = call(app, "GET", "/static/app.js")
    assert "Al Studio" in home.text
    assert "block-list" in home.text
    assert "scene-stage" in home.text
    assert "animation-preset" in home.text
    assert "timeline-visual" in home.text
    assert 'data-add="ambience"' in home.text
    assert "startRender" in script.text
    assert "previewAnimations" in script.text
    assert "sceneTimelineData" in script.text


def test_project_creation_opening_and_validated_script_save(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    created = create_demo(app)
    opened = call(app, "GET", "/api/projects/demo-story")
    listed = call(app, "GET", "/api/projects")
    assert created["name"] == "demo-story"
    assert opened.json()["script"]["scenes"][0]["events"][0]["speaker"] == "Narrator"
    assert listed.json() == [{"name": "demo-story", "title": "Demo Story"}]

    script = opened.json()["script"]
    script["scenes"][0]["events"].append(
        {
            "type": "action",
            "description": "Fade in",
            "start_seconds": 0,
            "duration_seconds": 1.5,
        }
    )
    saved = call(app, "PUT", "/api/projects/demo-story/script", json={"content": script})
    invalid = call(
        app,
        "PUT",
        "/api/projects/demo-story/script",
        json={"content": {"schema_version": 1, "scenes": []}},
    )
    escaped = call(app, "GET", "/api/projects/%2E%2E")
    assert saved.json() == {"status": "saved"}
    assert invalid.status_code == 422
    assert escaped.status_code in {400, 404}


def test_parallel_audio_tracks_require_a_configured_audio_asset(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    create_demo(app)
    project = call(app, "GET", "/api/projects/demo-story").json()["project"]
    script = call(app, "GET", "/api/projects/demo-story/script").json()
    script["scenes"][0]["events"].append(
        {
            "type": "ambience",
            "asset_id": "room-tone",
            "start_seconds": 0,
            "duration_seconds": 3,
        }
    )

    missing = call(app, "PUT", "/api/projects/demo-story/script", json={"content": script})
    imported = call(app, "POST", "/api/assets/audio?filename=room.wav", content=b"RIFF")
    project["assets"].append({"id": "room-tone", "kind": "audio", "path": imported.json()["path"]})
    saved_project = call(app, "PUT", "/api/projects/demo-story", json={"content": project})
    saved_script = call(app, "PUT", "/api/projects/demo-story/script", json={"content": script})

    assert missing.status_code == 422
    assert saved_project.status_code == 200
    assert saved_script.json() == {"status": "saved"}


def test_asset_import_is_type_checked_and_confined(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    imported = call(app, "POST", "/api/assets/characters?filename=hero.svg", content=b"<svg/>")
    traversal = call(
        app, "POST", "/api/assets/characters?filename=../escape.svg", content=b"<svg/>"
    )
    wrong_type = call(app, "POST", "/api/assets/characters?filename=notes.txt", content=b"no")
    duplicate = call(app, "POST", "/api/assets/characters?filename=hero.svg", content=b"<svg/>")
    assert imported.status_code == 201
    assert imported.json()["path"] == "characters/hero.svg"
    assert (tmp_path / "assets" / "characters" / "hero.svg").is_file()
    assert not (tmp_path / "escape.svg").exists()
    assert traversal.status_code == 400
    assert wrong_type.status_code == 415
    assert duplicate.status_code == 409


def test_scene_layout_can_be_saved_and_asset_previews_are_confined(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    create_demo(app)
    imported = call(app, "POST", "/api/assets/characters?filename=hero.svg", content=b"<svg/>")
    project = call(app, "GET", "/api/projects/demo-story").json()["project"]
    project["assets"].append({"id": "hero", "kind": "character", "path": "characters/hero.svg"})
    project["scenes"][0]["instances"] = [
        {
            "id": "hero-left",
            "asset_id": "hero",
            "x": 80,
            "y": 190,
            "width": 280,
            "height": 460,
            "rotation": 0,
            "opacity": 1,
            "z_index": 1,
            "visible": True,
        }
    ]
    project["scenes"][0]["animations"] = [
        {
            "id": "hero-enter",
            "target": "hero-left",
            "preset": "slide-in",
            "start_seconds": 0,
            "duration_seconds": 1.5,
            "easing": "ease-out",
            "direction": "left",
            "loop": False,
        }
    ]

    saved = call(app, "PUT", "/api/projects/demo-story", json={"content": project})
    reopened = call(app, "GET", "/api/projects/demo-story").json()["project"]
    preview = call(app, "GET", imported.json().get("url", "/asset-media/characters/hero.svg"))
    escaped = call(app, "GET", "/asset-media/%2E%2E/secret.svg")

    assert saved.json() == {"status": "saved"}
    assert reopened["scenes"][0]["instances"][0]["x"] == 80
    assert reopened["scenes"][0]["animations"][0]["preset"] == "slide-in"
    assert preview.content == b"<svg/>"
    assert escaped.status_code in {400, 404}


def test_voice_preview_returns_playable_local_media(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    preview = call(app, "POST", "/api/voice-preview", json={"text": "Hello", "voice": "af_heart"})
    assert preview.status_code == 200
    audio = call(app, "GET", preview.json()["url"])
    assert audio.status_code == 200
    assert audio.content.startswith(b"RIFF")
    assert call(app, "GET", "/media/%2E%2E/secret.wav").status_code in {400, 404}


def test_validation_dry_run_render_progress_and_artifacts(tmp_path: Path) -> None:
    app = make_app(tmp_path)
    create_demo(app)
    validation = call(app, "POST", "/api/projects/demo-story/validate")
    assert validation.json() == {"valid": True, "assets": 1, "scenes": 1}

    for dry_run, expected_kind in ((True, "dry-run"), (False, "render")):
        queued = call(
            app, "POST", f"/api/projects/demo-story/render?dry_run={str(dry_run).lower()}"
        )
        assert queued.status_code == 202
        job_id = queued.json()["job_id"]
        for _ in range(50):
            job = call(app, "GET", f"/api/renders/{job_id}").json()
            if job["status"] in {"complete", "failed"}:
                break
        assert job["status"] == "complete"
        assert job["kind"] == expected_kind
        assert job["progress"] == 100
        assert any(item["name"] == "metadata.json" for item in job["artifacts"])
        if not dry_run:
            video = next(item for item in job["artifacts"] if item["kind"] == "mp4")
            assert call(app, "GET", video["url"]).content == b"video"
