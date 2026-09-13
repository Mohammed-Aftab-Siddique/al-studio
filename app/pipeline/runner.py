"""Explicit, recoverable render stages for AL Studio."""
from dataclasses import asdict, dataclass
import json
from pathlib import Path
from app.animation import FrameRenderer
from app.audio.kokoro import KokoroVoiceEngine
from app.audio.mix import AudioMixer
from app.project import ProjectAssetManager
from app.script import DialogueTimelineBuilder, load_script
from app.video.compositor import VideoCompositor
from app.video.subtitles import SubtitleWriter

@dataclass(frozen=True)
class RenderResult:
    output_dir: Path
    video_path: Path | None
    dry_run: bool

class RenderPipeline:
    def __init__(self, asset_root: Path, voice_engine=None) -> None:
        self.assets = ProjectAssetManager(asset_root)
        self.voice_engine = voice_engine or KokoroVoiceEngine()
    def render(self, project_path: Path, script_path: Path, output_dir: Path, dry_run: bool = False) -> RenderResult:
        project = self.assets.load_project(project_path)
        asset_paths = self.assets.validate_assets(project)
        script = load_script(script_path)
        output_dir.mkdir(parents=True, exist_ok=True)
        if dry_run:
            self._metadata(output_dir, project.name, "dry-run", {"assets": sorted(asset_paths)})
            return RenderResult(output_dir, None, True)
        timeline = DialogueTimelineBuilder(self.voice_engine).build(project, script, output_dir)
        frames = FrameRenderer(project, asset_paths).render_sequence(timeline, output_dir / "frames")
        audio = AudioMixer().mix(timeline, output_dir / "audio" / "mix.wav")
        SubtitleWriter().write(timeline, output_dir / "subtitles" / "captions.srt")
        video = VideoCompositor().compose(output_dir / "frames" / "frame-%06d.svg", project.render.fps, audio, output_dir / "final" / f"{project.name}.mp4")
        self._metadata(output_dir, project.name, "complete", {"frames": len(frames), "video": str(video)})
        return RenderResult(output_dir, video, False)
    @staticmethod
    def _metadata(output_dir: Path, project: str, status: str, details: dict) -> None:
        (output_dir / "metadata.json").write_text(json.dumps({"project": project, "status": status, **details}, indent=2), encoding="utf-8")
