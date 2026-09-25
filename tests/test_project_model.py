from pathlib import Path

import pytest

from app.project import (
    AssetConfig,
    AssetResolutionError,
    ProjectAssetManager,
    ProjectConfig,
    ProjectConfigError,
)

ASSET_ROOT = Path("assets")
EXAMPLE_PROJECT = Path("projects/starter-project/project.json")


def test_starter_project_loads_and_resolves_all_reusable_assets() -> None:
    manager = ProjectAssetManager(ASSET_ROOT)

    project = manager.load_project(EXAMPLE_PROJECT)
    assets = manager.validate_assets(project)

    assert project.schema_version == 1
    assert project.render.fps == 24
    assert project.characters[0].voice_id == "am_adam"
    assert project.characters[0].visual_asset_id == "alex-visual"
    assert project.scenes[0].prop_asset_ids == ("plant",)
    assert set(assets) == {"alex-visual", "starter-room", "plant"}
    assert all(path.is_file() for path in assets.values())


def test_legacy_project_without_version_or_render_is_upgraded() -> None:
    project = ProjectConfig.from_dict(
        {
            "name": "legacy",
            "assets": [{"id": "hero", "kind": "character", "path": "characters/alex.svg"}],
            "characters": [{"name": "Alex", "voice": "am_adam", "visual_asset_id": "hero"}],
            "scenes": [],
        }
    )

    assert project.schema_version == 1
    assert project.characters[0].voice_id == "am_adam"
    assert project.render.width == 1280
    assert project.render.height == 720
    assert project.render.fps == 24


def test_future_schema_version_is_rejected() -> None:
    with pytest.raises(ProjectConfigError, match="unsupported schema version: 2"):
        ProjectConfig.from_dict({"schema_version": 2, "name": "future"})


def test_scene_instances_validate_placement_and_visual_asset_references() -> None:
    project = ProjectConfig.from_dict(
        {
            "schema_version": 1,
            "name": "composed",
            "assets": [
                {"id": "room", "kind": "scene", "path": "scenes/starter-room.svg"},
                {"id": "hero", "kind": "character", "path": "characters/alex.svg"},
            ],
            "characters": [],
            "scenes": [
                {
                    "id": "opening",
                    "background_asset_id": "room",
                    "instances": [
                        {
                            "id": "hero-left",
                            "asset_id": "hero",
                            "x": 90,
                            "y": 180,
                            "width": 280,
                            "height": 480,
                            "rotation": -4,
                            "opacity": 0.9,
                            "z_index": 3,
                        }
                    ],
                    "animations": [
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
                    ],
                }
            ],
        }
    )

    instance = project.scenes[0].instances[0]
    assert instance.instance_id == "hero-left"
    assert instance.rotation == -4
    assert instance.opacity == 0.9
    assert project.scenes[0].animations[0].target_instance_id == "hero-left"
    assert project.scenes[0].animations[0].duration_seconds == 1.5

    with pytest.raises(ProjectConfigError, match="unknown instance asset: missing"):
        ProjectConfig.from_dict(
            {
                "schema_version": 1,
                "name": "invalid-instance",
                "assets": [{"id": "room", "kind": "scene", "path": "scenes/starter-room.svg"}],
                "characters": [],
                "scenes": [
                    {
                        "id": "opening",
                        "background_asset_id": "room",
                        "instances": [
                            {
                                "id": "missing",
                                "asset_id": "missing",
                                "x": 0,
                                "y": 0,
                                "width": 100,
                                "height": 100,
                            }
                        ],
                    }
                ],
            }
        )


def test_character_visual_reference_must_exist_and_match_its_kind() -> None:
    with pytest.raises(ProjectConfigError, match="unknown character asset: missing"):
        ProjectConfig.from_dict(
            {
                "schema_version": 1,
                "name": "invalid",
                "assets": [],
                "characters": [
                    {"name": "Alex", "voice_id": "am_adam", "visual_asset_id": "missing"}
                ],
                "scenes": [],
            }
        )

    with pytest.raises(ProjectConfigError, match="asset room must have kind character"):
        ProjectConfig.from_dict(
            {
                "schema_version": 1,
                "name": "wrong-kind",
                "assets": [{"id": "room", "kind": "scene", "path": "scenes/starter-room.svg"}],
                "characters": [{"name": "Alex", "voice_id": "am_adam", "visual_asset_id": "room"}],
                "scenes": [],
            }
        )


@pytest.mark.parametrize("path", ["../outside.svg", "/tmp/outside.svg"])
def test_asset_paths_must_stay_inside_asset_root(path: str) -> None:
    with pytest.raises(ProjectConfigError, match="must stay within the asset root"):
        AssetConfig(asset_id="unsafe", kind="character", path=path)


def test_asset_manager_reports_missing_files_clearly(tmp_path: Path) -> None:
    manager = ProjectAssetManager(tmp_path)
    asset = AssetConfig(asset_id="missing", kind="character", path="characters/missing.svg")

    with pytest.raises(AssetResolutionError, match="asset file not found: characters/missing.svg"):
        manager.resolve_asset(asset)


def test_asset_manager_reports_incompatible_extensions_clearly(tmp_path: Path) -> None:
    file_path = tmp_path / "characters" / "invalid.txt"
    file_path.parent.mkdir()
    file_path.write_text("not an image", encoding="utf-8")
    manager = ProjectAssetManager(tmp_path)
    asset = AssetConfig(asset_id="invalid", kind="character", path="characters/invalid.txt")

    with pytest.raises(
        AssetResolutionError, match="incompatible extension .txt for kind character"
    ):
        manager.resolve_asset(asset)


def test_asset_manager_reports_invalid_json_clearly(tmp_path: Path) -> None:
    project_path = tmp_path / "project.json"
    project_path.write_text("{", encoding="utf-8")

    with pytest.raises(ProjectConfigError, match="invalid JSON"):
        ProjectAssetManager(tmp_path).load_project(project_path)
