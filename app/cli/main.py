"""Command-line entry point."""

import argparse
from pathlib import Path

from app.audio.kokoro import KokoroVoiceEngine
from app.pipeline import RenderPipeline
from app.project import ProjectAssetManager


def main() -> None:
    parser = argparse.ArgumentParser(prog="al-studio")
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("validate", "inspect-assets"):
        command = sub.add_parser(name)
        command.add_argument("project", type=Path)
        command.add_argument("--assets", type=Path, default=Path("assets"))
    render = sub.add_parser("render")
    render.add_argument("project", type=Path)
    render.add_argument("script", type=Path)
    render.add_argument("--assets", type=Path, default=Path("assets"))
    render.add_argument("--output", type=Path, default=Path("output/render"))
    render.add_argument("--dry-run", action="store_true")
    render.add_argument("--verbose", action="store_true")
    preview = sub.add_parser("voice-preview")
    preview.add_argument("--text", required=True)
    preview.add_argument("--voice", required=True)
    preview.add_argument("--output", type=Path, default=Path("output/voice-preview.wav"))
    args = parser.parse_args()
    if args.command in {"validate", "inspect-assets"}:
        manager = ProjectAssetManager(args.assets)
        project = manager.load_project(args.project)
        assets = manager.validate_assets(project)
        print(f"Valid: {project.name}")
        if args.command == "inspect-assets":
            for asset_id, path in assets.items():
                print(f"{asset_id}: {path}")
    elif args.command == "voice-preview":
        print(KokoroVoiceEngine().synthesize(args.text, args.voice, args.output))
    else:
        if args.verbose:
            print("Stages: validate → timeline → frames → audio → subtitles → MP4")
        result = RenderPipeline(args.assets).render(
            args.project, args.script, args.output, args.dry_run
        )
        print(f"{'Planned' if result.dry_run else 'Rendered'}: {result.output_dir}")


if __name__ == "__main__":
    main()
