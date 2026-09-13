# Starter Project

`project.json` is a schema-version 1 example configuration. Asset paths are
relative to the repository's `assets/` directory; they may not be absolute or
leave that asset root.

The example demonstrates:

- a reusable `alex-visual` character SVG;
- a persistent provider-neutral voice ID, `am_adam`;
- an explicit simple-mouth/idle-motion animation default;
- a reusable background and prop; and
- deterministic 1280 × 720 rendering defaults at 24 FPS.

The project/asset model is loaded with `ProjectAssetManager(asset_root)` and
validated through `ProjectConfig.from_dict()` or `load_project()`. Scripts and
rendering are deliberately not part of this example yet.
