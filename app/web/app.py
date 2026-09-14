"""Loopback-only HTTP API for the AL Studio browser workspace."""

from __future__ import annotations

import json
import mimetypes
import re
import threading
import uuid
from collections.abc import Callable
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response, StreamingResponse
from pydantic import BaseModel

from app.audio.kokoro import KokoroVoiceEngine
from app.pipeline import RenderPipeline
from app.project import AUDIO_EXTENSIONS, IMAGE_EXTENSIONS, ProjectAssetManager
from app.script import load_script, parse_script

WEB_DIR = Path(__file__).resolve().parent
DEFAULT_ROOT = Path.cwd()
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
CATEGORIES = frozenset({"characters", "scenes", "props", "audio", "music"})


class ProjectPayload(BaseModel):
    name: str


class ScriptPayload(BaseModel):
    content: dict[str, Any]


class VoicePayload(BaseModel):
    text: str
    voice: str


def _slug(value: str) -> str:
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9-]+", "-", value.lower())).strip("-")


def _within(root: Path, *parts: str) -> Path:
    resolved_root = root.resolve()
    candidate = resolved_root.joinpath(*parts).resolve()
    if not candidate.is_relative_to(resolved_root):
        raise HTTPException(400, "Path must stay inside the workspace")
    return candidate


def _json(path: Path) -> dict[str, Any]:
    try:
        content = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise HTTPException(404, f"File not found: {path.name}") from error
    except json.JSONDecodeError as error:
        raise HTTPException(400, f"Invalid JSON in {path.name}: {error.msg}") from error
    if not isinstance(content, dict):
        raise HTTPException(400, f"{path.name} must contain a JSON object")
    return content


def create_app(
    root: Path = DEFAULT_ROOT,
    pipeline_factory: Callable[[Path], RenderPipeline] = RenderPipeline,
    voice_engine_factory: Callable[[], Any] = KokoroVoiceEngine,
) -> FastAPI:
    """Build an app with injectable roots and engines for isolated tests."""
    workspace = root.resolve()
    projects_root = workspace / "projects"
    assets_root = workspace / "assets"
    output_root = workspace / "output"
    jobs: dict[str, dict[str, Any]] = {}
    jobs_lock = threading.Lock()

    web = FastAPI(title="AL Studio Web", docs_url=None, redoc_url=None)

    def project_path(name: str, filename: str) -> Path:
        if not name or name != _slug(name):
            raise HTTPException(400, "Invalid project name")
        return _within(projects_root, name, filename)

    def set_job(job_id: str, **changes: Any) -> None:
        with jobs_lock:
            jobs[job_id].update(changes)

    @web.get("/", response_class=HTMLResponse)
    async def home() -> HTMLResponse:
        return HTMLResponse((WEB_DIR / "index.html").read_text(encoding="utf-8"))

    @web.get("/static/{filename}")
    async def static_file(filename: str) -> Response:
        if filename not in {"app.css", "app.js"}:
            raise HTTPException(404, "Static file not found")
        path = WEB_DIR / "static" / filename
        media_type = "text/css" if path.suffix == ".css" else "text/javascript"
        return Response(path.read_bytes(), media_type=media_type)

    @web.get("/api/health")
    async def health() -> dict[str, str]:
        return {"status": "ready", "scope": "local-only"}

    @web.get("/api/projects")
    async def list_projects() -> list[dict[str, Any]]:
        if not projects_root.exists():
            return []
        result = []
        for config_path in sorted(projects_root.glob("*/project.json")):
            try:
                config = _json(config_path)
                result.append(
                    {
                        "name": config_path.parent.name,
                        "title": config.get("name", config_path.parent.name),
                    }
                )
            except HTTPException:
                result.append(
                    {
                        "name": config_path.parent.name,
                        "title": config_path.parent.name,
                        "invalid": True,
                    }
                )
        return result

    @web.post("/api/projects", status_code=201)
    async def create_project(payload: ProjectPayload) -> dict[str, Any]:
        name = _slug(payload.name)
        if not name:
            raise HTTPException(400, "Project name must contain letters or numbers")
        directory = _within(projects_root, name)
        if directory.exists():
            raise HTTPException(409, "A project with this name already exists")
        background_rel = f"scenes/{name}-stage.svg"
        background = _within(assets_root, background_rel)
        directory.mkdir(parents=True)
        background.parent.mkdir(parents=True, exist_ok=True)
        background.write_text(
            '<svg xmlns="http://www.w3.org/2000/svg" width="1280" height="720" '
            'viewBox="0 0 1280 720"><rect width="1280" height="720" fill="#17182b"/>'
            '<circle cx="1040" cy="145" r="230" fill="#715cff" opacity=".28"/>'
            '<path d="M0 590 Q320 500 640 590 T1280 570 V720 H0Z" fill="#242641"/></svg>\n',
            encoding="utf-8",
        )
        project = {
            "schema_version": 1,
            "name": payload.name.strip(),
            "assets": [{"id": "starter-stage", "kind": "scene", "path": background_rel}],
            "characters": [{"name": "Narrator", "voice_id": "af_heart"}],
            "scenes": [{"id": "opening", "background_asset_id": "starter-stage"}],
            "render": {"width": 1280, "height": 720, "fps": 24},
        }
        script = {
            "schema_version": 1,
            "scenes": [
                {
                    "scene_id": "opening",
                    "events": [
                        {
                            "type": "dialogue",
                            "speaker": "Narrator",
                            "text": "Welcome to your new story.",
                            "caption": "Welcome to your new story.",
                        }
                    ],
                }
            ],
        }
        (directory / "project.json").write_text(
            json.dumps(project, indent=2) + "\n", encoding="utf-8"
        )
        (directory / "script.json").write_text(
            json.dumps(script, indent=2) + "\n", encoding="utf-8"
        )
        return {"name": name, "project": project, "script": script}

    @web.get("/api/projects/{name}")
    async def open_project(name: str) -> dict[str, Any]:
        return {
            "name": name,
            "project": _json(project_path(name, "project.json")),
            "script": _json(project_path(name, "script.json")),
        }

    @web.get("/api/projects/{name}/script")
    async def get_script(name: str) -> dict[str, Any]:
        return _json(project_path(name, "script.json"))

    @web.put("/api/projects/{name}/script")
    async def save_script(name: str, payload: ScriptPayload) -> dict[str, str]:
        path = project_path(name, "script.json")
        if not project_path(name, "project.json").is_file():
            raise HTTPException(404, "Project not found")
        try:
            parse_script(payload.content)
        except ValueError as error:
            raise HTTPException(422, str(error)) from error
        path.write_text(json.dumps(payload.content, indent=2) + "\n", encoding="utf-8")
        return {"status": "saved"}

    @web.get("/api/assets")
    async def list_assets() -> list[dict[str, Any]]:
        if not assets_root.exists():
            return []
        return [
            {"path": str(path.relative_to(assets_root)), "size": path.stat().st_size}
            for path in sorted(assets_root.rglob("*"))
            if path.is_file()
        ]

    @web.post("/api/assets/{category}", status_code=201)
    async def import_asset(category: str, filename: str, request: Request) -> dict[str, Any]:
        if category not in CATEGORIES:
            raise HTTPException(400, "Invalid asset category")
        clean_name = Path(filename).name
        if clean_name != filename or clean_name.startswith(".") or not clean_name:
            raise HTTPException(400, "Invalid asset filename")
        allowed = AUDIO_EXTENSIONS if category in {"audio", "music"} else IMAGE_EXTENSIONS
        if Path(clean_name).suffix.lower() not in allowed:
            raise HTTPException(415, f"Allowed extensions: {', '.join(sorted(allowed))}")
        content = await request.body()
        if not content:
            raise HTTPException(400, "The selected file is empty")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(413, "Asset exceeds the 50 MB local import limit")
        target = _within(assets_root, category, clean_name)
        if target.exists():
            raise HTTPException(409, "An asset with this name already exists")
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(content)
        return {"path": str(target.relative_to(assets_root)), "size": len(content)}

    @web.post("/api/voice-preview")
    async def voice_preview(payload: VoicePayload) -> dict[str, str]:
        if not payload.text.strip() or not payload.voice.strip():
            raise HTTPException(422, "Text and voice are required")
        preview_id = uuid.uuid4().hex
        output = _within(output_root, "web", "previews", f"{preview_id}.wav")
        try:
            voice_engine_factory().synthesize(payload.text.strip(), payload.voice.strip(), output)
        except Exception as error:
            raise HTTPException(500, f"Voice preview failed: {error}") from error
        return {"url": f"/media/web/previews/{preview_id}.wav", "path": str(output)}

    @web.post("/api/projects/{name}/validate")
    async def validate_project(name: str) -> dict[str, Any]:
        try:
            manager = ProjectAssetManager(assets_root)
            project = manager.load_project(project_path(name, "project.json"))
            assets = manager.validate_assets(project)
            script = load_script(project_path(name, "script.json"))
            scene_ids = {scene.scene_id for scene in project.scenes}
            speakers = {character.name for character in project.characters}
            for scene in script.scenes:
                if scene.scene_id not in scene_ids:
                    raise ValueError(f"Script references unknown scene: {scene.scene_id}")
                for event in scene.events:
                    speaker = getattr(event, "speaker", None)
                    if speaker is not None and speaker not in speakers:
                        raise ValueError(f"Script references unknown speaker: {speaker}")
        except (OSError, ValueError) as error:
            raise HTTPException(422, str(error)) from error
        return {"valid": True, "assets": len(assets), "scenes": len(script.scenes)}

    @web.post("/api/projects/{name}/render", status_code=202)
    async def render(name: str, dry_run: bool = False) -> dict[str, str]:
        project = project_path(name, "project.json")
        script = project_path(name, "script.json")
        if not project.is_file() or not script.is_file():
            raise HTTPException(404, "Project or script not found")
        job_id = uuid.uuid4().hex
        output_dir = _within(output_root, "web", name, job_id)
        jobs[job_id] = {
            "id": job_id,
            "project": name,
            "kind": "dry-run" if dry_run else "render",
            "status": "queued",
            "stage": "queued",
            "progress": 0,
            "artifacts": [],
            "error": None,
        }

        def run() -> None:
            try:
                set_job(job_id, status="running")
                result = pipeline_factory(assets_root).render(
                    project,
                    script,
                    output_dir,
                    dry_run,
                    lambda stage, percent: set_job(job_id, stage=stage, progress=percent),
                )
                artifacts = []
                for path in sorted(result.output_dir.rglob("*")):
                    if path.is_file() and path.suffix.lower() in {".mp4", ".wav", ".srt", ".json"}:
                        relative = path.relative_to(output_root).as_posix()
                        artifacts.append(
                            {
                                "name": path.name,
                                "url": f"/media/{quote(relative)}",
                                "kind": path.suffix[1:],
                            }
                        )
                set_job(
                    job_id, status="complete", stage="complete", progress=100, artifacts=artifacts
                )
            # A background-job boundary must convert every pipeline failure into
            # state the browser can report instead of losing it in the thread.
            except Exception as error:  # noqa: BLE001
                set_job(job_id, status="failed", stage="failed", error=str(error))

        threading.Thread(target=run, name=f"al-studio-{job_id[:8]}", daemon=True).start()
        return {"job_id": job_id}

    @web.get("/api/renders/{job_id}")
    async def render_status(job_id: str) -> dict[str, Any]:
        with jobs_lock:
            job = jobs.get(job_id)
            if job is None:
                raise HTTPException(404, "Render job not found")
            return dict(job)

    @web.get("/media/{relative_path:path}")
    async def media(relative_path: str) -> StreamingResponse:
        path = _within(output_root, relative_path)
        if not path.is_file():
            raise HTTPException(404, "Output file not found")

        async def chunks():
            with path.open("rb") as stream:
                while chunk := stream.read(1024 * 1024):
                    yield chunk

        media_type = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
        return StreamingResponse(chunks(), media_type=media_type)

    return web


app = create_app()
