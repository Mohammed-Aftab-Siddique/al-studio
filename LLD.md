# AL Studio — Low-Level Design

> Pipeline design aligned with `GOALS.md`. Status reflects the repository on
> 2026-09-14: the deterministic render pipeline, CLI, and first local browser
> milestone are implemented and tested.

## Design Principles

- The render path is local-first and CPU-capable.
- Reusable, deterministic assets and timelines define the output.
- AI assistance is optional and must produce editable/reusable artifacts;
  it is never required for the core render path.
- TTS providers are isolated behind `VoiceEngine`.
- Each stage receives validated input, produces a named artifact, and emits
  actionable errors rather than silently continuing.

## End-to-End Pipeline

```mermaid
flowchart TD
    input[User input<br/>project configuration + assets + script + render settings]
    validate[Project validation]
    manager[Project / Asset Manager]
    schema[Project, character, scene, and asset schemas]
    script[Script parser]
    timeline[Dialogue and scene timeline builder]
    character[Character system]
    voice[Voice Engine]
    kokoro[KokoroVoiceEngine<br/>implemented]
    audioLines[Dialogue WAV files + durations]
    scene[Scene Engine]
    animation[2D Animation Engine]
    frames[Rendered frame sequence]
    audio[Audio Engine]
    mix[Mixed audio track]
    captions[Subtitle generator]
    subtitles[SRT and optional burned-in captions]
    compositor[Compositor / Video Engine]
    mp4[Final MP4 + render metadata]
    cli[CLI / Automation]
    web[Local Browser App]
    api[Loopback API + background jobs]

    input --> validate
    validate --> manager
    manager --> schema
    schema --> script
    script --> timeline
    schema --> character
    character --> timeline
    timeline --> voice
    voice --> kokoro
    kokoro --> audioLines
    timeline --> scene
    character --> animation
    scene --> animation
    timeline --> animation
    animation --> frames
    audioLines --> audio
    timeline --> audio
    audio --> mix
    timeline --> captions
    captions --> subtitles
    frames --> compositor
    mix --> compositor
    subtitles --> compositor
    compositor --> mp4
    cli --> validate
    cli --> compositor
    web --> api
    api --> validate
    api --> compositor
    mp4 --> api
    api --> web

    classDef implemented fill:#c8e6c9,stroke:#2e7d32,color:#1b5e20;
    classDef planned fill:#e3f2fd,stroke:#1565c0,color:#0d47a1;
    class kokoro,validate,manager,schema,script,timeline,character,voice,audioLines,input,scene,animation,frames,audio,mix,captions,subtitles,compositor,mp4,cli,web,api implemented;
```

Green is implemented today. The CLI and loopback browser API both call the
same `RenderPipeline`; the web layer adds project/script persistence, guarded
asset imports, background-job progress, and local media delivery without
duplicating render-domain logic.

## Browser Interaction Flow

```mermaid
flowchart LR
    launch[al-studio-web] --> loopback[127.0.0.1<br/>port 8177–8187]
    loopback --> projects[Create / open project]
    projects --> editor[Block script editor]
    projects --> library[Safe asset import]
    projects --> preview[Playable voice preview]
    editor --> save[Validated script save]
    library --> assetRoot[assets/category/file]
    preview --> previewWav[output/web/previews/*.wav]
    save --> preflight[Project + script + asset validation]
    preflight --> dryrun[Dry-run metadata]
    preflight --> job[Background render job]
    job --> stages[Stage + percent + errors]
    stages --> results[MP4 / WAV / SRT / metadata]
    results --> player[Embedded playback + downloads]
```

The HTTP layer accepts only project slugs and root-relative media paths.
Asset imports sanitize filenames, enforce category-specific extensions and a
50 MB limit, reject duplicates, and resolve every target beneath `assets/`.
Generated media is served only from `output/`.

## Inputs and Persistent Project Model

The project configuration is the source of truth. It should be versioned,
human-editable, validated before rendering, and contain references rather
than copied asset content.

```mermaid
flowchart LR
    project[Project config]
    settings[Render settings<br/>resolution, FPS, output options]
    characters[Character configs<br/>name, asset refs, voice ID, animation defaults]
    scenes[Scene configs<br/>background, props, camera]
    script[Script<br/>scene order, dialogue, actions, ambience, captions]
    assets[Asset files<br/>characters, scenes, props, music, SFX]
    validator[Schema + asset validation]
    model[Validated internal project model]

    project --> settings
    project --> characters
    project --> scenes
    project --> script
    characters --> validator
    scenes --> validator
    script --> validator
    assets --> validator
    settings --> validator
validator --> model
```

### Scene instance model

Reusable visual assets are placed through scene instances rather than having
coordinates baked into the source files. Each instance owns an ID, asset
reference, X/Y position, width, height, rotation, opacity, visibility, and
z-index. The browser stage and SVG renderer both use the render coordinate
system, so saved layout values are WYSIWYG.

```mermaid
flowchart LR
    library[Reusable visual asset] --> drag[Browser drag and drop]
    drag --> instance[SceneInstance<br/>transform + layer]
    inspector[Move / resize / exact inspector] --> instance
    instance --> project[Validated project.json]
    project --> renderer[SVG frame renderer]
    renderer --> frame[Identical positioned frame]
```

Characters with a matching scene instance retain that placement when dialogue
mouth animation is active. Older `prop_asset_ids` remain supported and can be
migrated into explicit instances by the Scene workspace.

### Scene animation clip model

Universal animation clips are validated children of a scene and refer to a
`SceneInstance` by ID. Both the browser preview and final SVG renderer evaluate
the same preset contract using scene-local time.

```mermaid
flowchart LR
    controls[Preset + delay + duration<br/>easing + direction + loop]
    controls --> clip[SceneAnimation]
    clip --> project[Validated project.json]
    project --> browser[Browser preview evaluator]
    project --> renderer[Deterministic frame evaluator]
    browser --> transform[Position / scale / rotation / opacity]
    renderer --> transform
    transform --> output[Preview and rendered frame parity]
```

Clips may overlap on the same instance; translation and rotation are added,
scale and opacity are multiplied. The available universal presets are fade
in/out, slide in, bounce, float, pulse, rotate, and shake. Parallel visual,
dialogue, caption, and audio tracks share the same scene-local clock.

### Asset capability manifests

Visual asset entries may declare named sprite-sheet and frame-sequence
capabilities. The project loader validates manifest shape, safe asset-relative
paths, frame metadata, FPS, and unique IDs. Scene asset clips are then checked
against the selected instance's asset, preventing a character from selecting
an animation it does not own.

```mermaid
flowchart LR
    files[Imported sprite sheet<br/>or ordered frame files]
    manifest[Asset capability manifest<br/>ID + format + FPS + loop]
    files --> validator[Safe path and image validation]
    manifest --> validator
    validator --> dropdown[Asset-specific animation dropdown]
    dropdown --> clip[SceneAnimation<br/>preset: asset]
    clip --> browser[Browser frame selector]
    clip --> renderer[SVG frame selector]
    browser --> parity[Matching deterministic frame]
    renderer --> parity
```

Universal transform presets remain available alongside declared asset motion.
The capability's frame count and FPS provide a natural duration default, while
each scene clip retains editable delay, duration, and loop settings.

### Layered and skeletal rigs

An optional rig capability turns a visual asset into a hierarchy of reusable
image layers. Each part owns a local pivot and may attach to another part;
named poses provide normalized keyframes for local translation, rotation,
scale, and opacity. Project validation rejects unsafe files, missing parents,
cycles, unknown keyframed parts, duplicate IDs, and invalid time ranges.

```mermaid
flowchart LR
    parts[Imported part images] --> rig[Validated rig hierarchy]
    poses[Named normalized keyframes] --> rig
    rig --> picker[Asset-specific pose dropdown]
    picker --> clip[SceneAnimation<br/>preset: rig]
    clip --> clock[Scene-local pose clock]
    clock --> interpolation[Interpolate local transforms]
    interpolation --> hierarchy[Apply parent then child transforms]
    hierarchy --> browser[Browser SVG preview]
    hierarchy --> renderer[Rendered SVG frames]
```

Rig poses affect pixels inside an instance while universal presets continue to
affect the complete instance. This separation permits a waving arm and a
whole-character slide or bounce to run together without browser-only state.

### Proposed responsibility boundaries

| Component | Owns | Must not own |
| --- | --- | --- |
| Project/Asset Manager | Loading project files, resolving asset paths, missing-asset errors | Rendering logic or TTS-provider details |
| Character System | Stable character identity, visual references, voice ID, animation defaults | Kokoro pipeline initialization |
| Script Engine | Script parsing, speaker/action validation, timeline events | Pixel/frame rendering |
| Voice Engine | Converting one text segment to audio through a provider | Character lookup or scene timing policy |
| Scene/Animation Engines | Visual state and deterministic frames | Audio mixing or MP4 encoding |
| Audio Engine | Dialogue alignment, ambience/SFX/music mixing | Character rendering |
| Compositor/Video Engine | Combining frames, audio, captions, and FFmpeg output | Project semantics |
| CLI/Pipeline | Stage orchestration, user-facing progress, output locations | Duplicated domain logic |

## Render-Stage Contract

Each stage writes only inside a render-specific output directory. The
pipeline records stage inputs, produced paths, duration/timing metadata,
and failures so a render can be inspected and retried.

```mermaid
sequenceDiagram
    participant User
    participant CLI as CLI / Pipeline
    participant PM as Project Manager
    participant SE as Script Engine
    participant VE as Voice Engine
    participant AE as Animation + Scene
    participant AU as Audio Engine
    participant CO as Compositor

    User->>CLI: render example-project
    CLI->>PM: load and validate config + assets
    PM-->>CLI: validated project model
    CLI->>SE: parse script and build timeline
    SE-->>CLI: validated timeline events
    CLI->>VE: synthesize each dialogue event
    VE-->>CLI: WAV paths + measured durations
    CLI->>SE: finalize dialogue timings
    CLI->>AE: render scenes and animation frames
    AE-->>CLI: frame sequence
    CLI->>AU: mix dialogue, ambience, SFX, music
    AU-->>CLI: final audio track
    CLI->>CO: encode frames + audio + captions
    CO-->>CLI: MP4 + render metadata
    CLI-->>User: output paths and summary
```

## Voice Engine Design

Current implementation:

```text
app/audio/
├── voice.py     VoiceEngine abstract interface
├── kokoro.py    KokoroVoiceEngine implementation
└── __init__.py
```

`VoiceEngine.synthesize(text, voice, output_path) -> Path` is the
provider-neutral boundary. `KokoroVoiceEngine` currently creates a CPU
`KPipeline`, writes mono PCM-16 WAV output at 24 kHz, creates the parent
output directory, and returns the output path.

The voice boundary rejects empty or non-string text/voice IDs and invalid
output paths before calling a provider. The Kokoro adapter requires a `.wav`
path and wraps provider or audio-writing failures in `VoiceSynthesisError`.
An injected pipeline is supported for fast unit tests; production continues
to construct the real Kokoro pipeline by default.

The next character layer should hold a stable logical `voice_id` value,
such as `am_adam`. The character system passes that value to `VoiceEngine`;
it must not import or configure `KokoroVoiceEngine` directly.

```mermaid
flowchart LR
    char[Character config<br/>voice_id: am_adam]
    dialogue[Dialogue event<br/>speaker + text]
    resolver[Character / dialogue resolver]
    interface[VoiceEngine]
    provider[KokoroVoiceEngine]
    wav[WAV artifact<br/>path + measured duration]

    char --> resolver
    dialogue --> resolver
    resolver --> interface
    interface --> provider
    provider --> wav
```

## Timeline Model

The timeline is the common contract between dialogue, animation, audio,
captions, and composition. Every event should have a deterministic start
time, duration, scene identifier, and payload specific to its event type.

```text
TimelineEvent
  id
  type: animation | dialogue | action | ambience | sound_effect | caption
  track: visual | dialogue | caption | audio
  scene_id
  start_seconds
  duration_seconds
  scene_start_seconds
  scene_duration_seconds
  payload
```

For dialogue, the payload should include the speaker ID, text, generated
WAV path, and caption text. Generated WAV duration becomes the dialogue
duration; the same time interval drives mouth animation, audio placement,
and subtitle timing.

The builder first resolves scene-local scheduling. An explicit
`start_seconds` places an event independently; an omitted start advances from
the furthest endpoint for backwards-compatible sequential scripts. It then
adds project animation clips to the visual track, calculates the scene window,
and offsets the next scene. The renderer selects the scene window separately
from the active dialogue, so mouth animation and visual clips can overlap.

```mermaid
flowchart LR
    starts[Explicit or automatic starts] --> plan[Scene-local timeline plan]
    animations[Project animations] --> visual[Visual track]
    script[Script events] --> plan
    plan --> visual
    plan --> dialogue[Dialogue track]
    plan --> captions[Caption track]
    plan --> audio[Audio track]
    visual --> render[Frame renderer]
    dialogue --> render
    dialogue --> mix[Audio mixer]
    audio --> mix
    captions --> srt[Subtitle writer]
```

## Output Layout

The final path names may evolve, but the pipeline should keep all
intermediate artifacts grouped under one render ID.

```text
output/
└── <project-name>-<render-id>/
    ├── metadata.json
    ├── validation.json
    ├── timeline.json
    ├── dialogue/
    │   └── <event-id>.wav
    ├── frames/
    │   └── <frame-number>.png
    ├── audio/
    │   └── mix.wav
    ├── subtitles/
    │   └── captions.srt
    └── final/
        └── <project-name>.mp4
```

## Planned Delivery Slices

1. **Minimal vertical slice:** one static scene, one character, generated
   dialogue WAV, timed mouth animation, subtitles, and MP4 rendering.
2. **Multi-scene production:** add multiple characters, props, transitions,
   ambience, sound effects, and music mixing.
3. **Release hardening:** CLI, dry-run/verbose modes, reproducibility,
   logging, full test layers, documentation, CPU benchmark, and licensing
   review.
4. **Optional AI helpers:** add only after the deterministic pipeline works
   independently.

## Completion Checks

The first release is ready when the reference example can be rendered from a
clean local setup with one documented command, produces an MP4 containing
video and synchronized audio, provides subtitles, preserves distinct
character voices across scenes, and passes unit, integration, and
end-to-end tests.
