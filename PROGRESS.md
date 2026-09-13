# AL Studio --- PROGRESS

> Durable project log of completed work, architectural decisions, setup,
> troubleshooting, and next steps.
>
> Last updated: 2026-09-13

## 1. Project Vision

**AL Studio** is an open-source, local-first, script-driven 2D animation
studio.

Target capabilities:

-   Consistent reusable cartoon characters
-   Persistent, distinct voices per character
-   Backgrounds and scenes
-   Dialogue-driven animation
-   Ambience and sound effects
-   Subtitles
-   Final MP4 rendering
-   Script-driven automation and a future CLI

Agreed high-level pipeline:

``` text
User Input
  Characters + Scenes + Script + Settings
        ↓
1. Project / Asset Manager
2. Script Engine
3. Voice Engine
4. 2D Animation Engine
5. Scene Engine
6. Audio Engine
7. Compositor / Video Engine
8. Automation / CLI
        ↓
Video
```

## 2. Major Decisions

### Visual direction

Selected: **Option B --- Modern Minimal Cartoon**.

The project is not targeting realistic 3D animation. The initial system
will be a practical 2D cartoon pipeline.

### Core architecture

> **Deterministic 2D animation is the core; AI is used as supporting
> services.**

Character identity, scene layout, timing, animation, audio placement,
and rendering should not require regenerating everything with AI for
every video.

Reusable assets and deterministic behavior are preferred wherever
consistency matters.

AI can later assist with script generation, backgrounds, character
generation, creative suggestions, and other production accelerators.

### Character consistency

Characters should use reusable assets/configuration rather than being
regenerated from scratch for each scene.

Persistent identity will eventually cover both visual identity and voice
identity.

### Voice architecture

Text-to-speech must sit behind an AL Studio abstraction rather than
coupling the application directly to Kokoro.

Kokoro is the first backend, but other engines should be swappable
later.

For Kokoro, **voice IDs are the persistence mechanism for character
voices**. No separate voice "seed" system is needed.

### Git workflow

Git should be used properly, but branching will be introduced only when
it naturally becomes useful, such as for a substantial experiment or
parallel feature. Branches will not be created merely as a Git exercise.

### GitHub

There is no need to push to GitHub yet. Development remains local until
a remote provides a concrete benefit.

### Docker

Docker and Docker Compose are installed, but Docker is intentionally not
kept running at boot because it slows laptop startup/shutdown.

Do not require Docker for normal AL Studio development unless a future
component genuinely benefits from it.

------------------------------------------------------------------------

## 3. Agreed Repository Structure

``` text
al-studio/
├── app/
│   ├── cli/
│   ├── script/
│   ├── characters/
│   ├── animation/
│   ├── scenes/
│   ├── audio/
│   ├── video/
│   └── pipeline/
├── assets/
│   ├── characters/
│   ├── scenes/
│   ├── props/
│   ├── audio/
│   └── music/
├── projects/
├── workflows/
├── output/
├── tests/
├── pyproject.toml
└── README.md
```

Keep this stable unless an architectural change is deliberately
discussed and committed.

## 4. Roadmap

  Phase   Area                                   Status
  ------- -------------------------------------- -----------------
  0       Hardware / environment assessment      **Done**
  1       Development environment / foundation   **Done**
  2       Voice engine                           **In progress**
  3       Character system                       Planned
  4       Animation engine                       Planned
  5       Scene engine                           Planned
  6       Dialogue synchronization               Planned
  7       Audio engine                           Planned
  8       Compositor                             Planned
  9       Script format                          Planned
  10      Automation                             Planned
  11      Character consistency                  Planned
  12      AI enhancements                        Planned

Current position: **Script and Dialogue complete**. The Voice Engine,
Project/Asset Model, and Script/Dialogue milestones are complete.
Deterministic 2D rendering is next.

# Phase 0 --- Hardware and Environment

Established development environment:

-   Linux Mint 22.3 (Zena), Ubuntu codename `noble`
-   Python 3.12.3
-   Git 2.43.0
-   FFmpeg 6.1.1-3ubuntu5
-   Docker 29.7.2
-   Docker Compose v5.5.0
-   Node.js v22.23.2
-   npm 10.9.8
-   16 GiB RAM; approximately 12 GiB available during assessment
-   Root filesystem approximately 468 GB total; approximately 255 GB
    free
-   Display: 2880 × 1800
-   Intel Raptor Lake-P Iris Xe integrated GPU
-   Mesa/i915 graphics stack
-   No NVIDIA/AMD discrete GPU

### Hardware implication

There is no CUDA-capable NVIDIA GPU. The initial local AI/TTS stack
therefore needs to work well on CPU.

The core animation architecture must not depend on GPU-heavy generative
models.

# Phase 1 --- Project Foundation

## Project root

``` text
~/Projects/open-source/al-studio
```

## Initial setup

``` bash
mkdir -p ~/Projects
cd ~/Projects
mkdir al-studio
cd al-studio
git init

mkdir -p     app/cli     app/script     app/characters     app/animation     app/scenes     app/audio     app/video     app/pipeline     assets/characters     assets/scenes     assets/props     assets/audio     assets/music     projects     workflows     output     tests

touch README.md
touch pyproject.toml
python3 -m venv .venv
source .venv/bin/activate
```

The repository is currently used from
`~/Projects/open-source/al-studio`.

## Python command behavior

The host does not expose a system-wide `python` command.

Outside the venv use:

``` bash
python3
```

Inside `.venv` use:

``` bash
python
```

## `.gitignore`

Configured as:

``` gitignore
# Python
__pycache__/
*.py[cod]
*.egg-info/

# Virtual environment
.venv/

# Environment / secrets
.env
.env.*

# Generated output
output/*
!output/.gitkeep

# Generated media
*.mp4
*.mov
*.mkv
*.webm
*.wav
*.mp3

# AI model files
*.safetensors
*.ckpt
*.pth
*.onnx
*.gguf

# Caches
.cache/
.pytest_cache/
.mypy_cache/

# OS
.DS_Store
Thumbs.db
```

`output/.gitkeep` was created so the output directory remains in Git
while generated output is ignored.

## Git checkpoints

Known initial commit:

``` text
de46e6e chore: initialize animation studio
```

Git identity was configured successfully.

The project configuration checkpoint used:

``` bash
git add pyproject.toml
git commit -m "chore: configure Python project"
```

Its exact hash was not captured in the conversation.

The Kokoro test checkpoint used:

``` bash
git add tests/test_kokoro.py
git commit -m "test: verify Kokoro voice generation"
```

That work was subsequently treated as complete, but its exact hash was
not captured.

The Voice Engine abstraction checkpoint was proposed as:

``` bash
git status
git add app/audio tests/test_voice_engine.py
git commit -m "feat: add voice engine abstraction"
git log --oneline -3
```

The conversation has **not yet captured the output of that commit**, so
this file does not claim a commit hash or confirmed completion of that
Git checkpoint.

## `pyproject.toml`

Configured as:

``` toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "al-studio"
version = "0.1.0"
description = "Script-driven 2D animation studio"
requires-python = ">=3.12,<3.13"

[tool.setuptools.packages.find]
where = ["."]
include = ["app*"]
```

Installed editable:

``` bash
pip install -e .
```

Result: `al-studio-0.1.0` installed successfully.

### Python version decision

`>=3.12,<3.13` is a current compatibility/reproducibility constraint,
particularly around Kokoro, not a permanent architectural requirement.

Revisit Python 3.13+ when dependencies support it reliably and tests
demonstrate compatibility.

# Phase 2 --- Voice Engine

## Objective

Build a local TTS layer capable of giving characters stable, distinct
voices while keeping the rest of AL Studio independent of a specific TTS
implementation.

## 2.1 --- System dependencies

FFmpeg:

``` bash
sudo apt update
sudo apt install ffmpeg
```

Verified:

``` text
ffmpeg version 6.1.1-3ubuntu5
```

eSpeak NG:

``` bash
sudo apt update
sudo apt install espeak-ng
```

Verified:

``` text
eSpeak NG text-to-speech: 1.51
Data at: /usr/lib/x86_64-linux-gnu/espeak-ng-data
```

## 2.2 --- Kokoro

Installed inside `.venv`:

``` bash
pip install "kokoro>=0.9.4" soundfile
```

Import check:

``` bash
python -c "from kokoro import KPipeline; print('Kokoro import OK')"
```

Result:

``` text
Kokoro import OK
```

### Kokoro findings/decisions

The evaluated Kokoro package:

-   Is approximately 82M parameters
-   Is open-weight
-   Uses an Apache license
-   Supports the current Python 3.12 environment
-   Produces 24 kHz audio in the tested pipeline
-   Provides multiple voice IDs
-   Runs on CPU
-   Can use CUDA when available

The current laptop has no CUDA GPU, so AL Studio explicitly uses
`device="cpu"`.

No manual model download was needed. Required assets were downloaded
lazily on first synthesis.

Observed Hugging Face cache usage after setup was approximately 314 MB.

Male voice IDs identified included:

American:

``` text
am_adam
am_echo
am_eric
am_fenrir
am_liam
am_michael
am_onyx
am_puck
```

British:

``` text
bm_daniel
bm_fable
bm_george
bm_lewis
```

Decision: characters will eventually persist a voice ID such as
`am_adam`.

## Initial voice test

Created `tests/test_kokoro.py`:

``` python
from pathlib import Path

import soundfile as sf
from kokoro import KPipeline


OUTPUT_DIR = Path("output/voice-tests")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

pipeline = KPipeline(lang_code="a", device="cpu")

tests = {
    "adam": ("am_adam", "Hello, my friends. It's good to see you."),
    "michael": ("am_michael", "Hello, my friends. It's good to see you."),
    "puck": ("am_puck", "Hello, my friends. It's good to see you."),
}

for name, (voice, text) in tests.items():
    output_path = OUTPUT_DIR / f"{name}.wav"

    with sf.SoundFile(
        output_path,
        mode="w",
        samplerate=24000,
        channels=1,
        subtype="PCM_16",
    ) as audio_file:
        for result in pipeline(text, voice=voice):
            audio_file.write(result.audio.numpy())

    print(f"Created: {output_path}")
```

Generated and manually compared:

-   `am_adam`
-   `am_michael`
-   `am_puck`

They were confirmed to sound distinctly different.

This validated the persistent multi-character voice requirement.

Generated `.wav` files are ignored by Git; source/test code is tracked.

# 2.3 --- Voice Engine Abstraction

Created:

``` text
app/audio/
├── __init__.py
├── kokoro.py
└── voice.py
```

## Generic interface

`app/audio/voice.py`:

``` python
from abc import ABC, abstractmethod
from pathlib import Path


class VoiceEngine(ABC):
    """Interface for text-to-speech engines."""

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> Path:
        """Convert text to speech and save it to output_path."""
        raise NotImplementedError
```

## Kokoro implementation

`app/audio/kokoro.py`:

``` python
from pathlib import Path

import soundfile as sf
from kokoro import KPipeline

from .voice import VoiceEngine


class KokoroVoiceEngine(VoiceEngine):
    """Kokoro implementation of the AL Studio voice engine."""

    SAMPLE_RATE = 24000

    def __init__(self, lang_code: str = "a", device: str = "cpu") -> None:
        self.pipeline = KPipeline(
            lang_code=lang_code,
            device=device,
        )

    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> Path:
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with sf.SoundFile(
            output_path,
            mode="w",
            samplerate=self.SAMPLE_RATE,
            channels=1,
            subtype="PCM_16",
        ) as audio_file:
            for result in self.pipeline(text, voice=voice):
                audio_file.write(result.audio.numpy())

        return output_path
```

Implementation decisions:

-   Kokoro-specific code is isolated.
-   Application code can depend on `VoiceEngine`.
-   Output directories are automatically created.
-   Output is mono PCM-16 WAV.
-   Sample rate is 24 kHz.
-   CPU is the current default.
-   `synthesize()` returns the generated `Path`.

Import verification succeeded twice:

``` bash
python -c "from app.audio.kokoro import KokoroVoiceEngine; print('Voice engine OK')"
```

Result:

``` text
Voice engine OK
```

## 2.3.3 --- Integration test

Created `tests/test_voice_engine.py`:

``` python
from pathlib import Path

from app.audio.kokoro import KokoroVoiceEngine


def test_kokoro_generates_audio() -> None:
    output_path = Path("output/voice-tests/abstraction.wav")

    engine = KokoroVoiceEngine()

    result = engine.synthesize(
        text="This audio was generated through the AL Studio voice engine.",
        voice="am_adam",
        output_path=output_path,
    )

    assert result == output_path
    assert output_path.exists()
    assert output_path.stat().st_size > 0
```

Correct invocation:

``` bash
python -m pytest tests/test_voice_engine.py -v
```

Observed twice:

``` text
collected 1 item
tests/test_voice_engine.py::test_kokoro_generates_audio PASSED [100%]

1 passed, 5 warnings in 12.02s
```

This confirms initialization, synthesis, output-directory creation,
non-empty WAV generation, and correct return path through the AL Studio
abstraction.

## Warnings observed

Five third-party warnings appeared:

1.  PyTorch LSTM dropout warning: non-zero dropout with one recurrent
    layer.
2.  PyTorch `torch.nn.utils.weight_norm` FutureWarning.
3.  `torch.jit.script` deprecation warning.
4.  Misaki `importlib.resources.open_text` deprecation for one English
    resource.
5.  Misaki `importlib.resources.open_text` deprecation for another
    English resource.

Decision:

> These are upstream dependency warnings, not AL Studio failures. Do not
> modify or suppress upstream behavior just to obtain warning-free
> output. Revisit if upgrades or functional compatibility issues make
> them relevant.

# Troubleshooting / Lessons Learned

### `python3` vs `python`

Use `python3` on the host and `python` after activating `.venv`.

### Editable install

`pip install -e .` lets project modules be imported while source files
are edited without reinstalling after every change.

### Isolate import problems

The direct `python -c` import check was used to distinguish
package/import problems from synthesis problems.

### Pytest must execute test functions

Running a file containing a pytest function as a normal Python script
does not automatically execute that test. Use:

``` bash
python -m pytest tests/test_voice_engine.py -v
```

### Generated media stays out of Git

Voice-test WAVs and future rendered media are generated artifacts, not
source files. `.gitignore` already handles them.

### First synthesis may download assets

Successful import does not mean all Kokoro assets are cached. First
synthesis can trigger lazy downloads.

### CPU execution is intentional

CPU mode is the correct current configuration for the Intel
integrated-GPU development laptop.

### Dependency warnings are not project failures

The integration test passes. Current warnings originate from
dependencies and are tracked separately from AL Studio defects.

# Current State

Completed:

-   Phase 0 hardware/environment assessment
-   Repository and directory structure
-   Python virtual environment
-   Git ignore/generated-output policy
-   Python packaging configuration
-   Editable installation
-   FFmpeg setup
-   eSpeak NG setup
-   Kokoro installation/import
-   First real Kokoro synthesis
-   Multiple voice comparison
-   Confirmation that tested voices sound different
-   Stable voice-ID persistence decision
-   Generic `VoiceEngine` interface
-   `KokoroVoiceEngine`
-   Voice-engine import verification
-   Real synthesis pytest
-   Successful test twice

Current phase: **Phase 2 --- Voice Engine**.

# 2.4 --- Character Voice Configuration

Created `app/characters/character.py` and `app/characters/__init__.py`.

`CharacterConfig` is an immutable, provider-neutral character identity
model:

```python
CharacterConfig(name="Alex", voice_id="am_adam")
```

It persists the voice ID without importing Kokoro or coupling character code
to any TTS provider. It rejects empty, non-string, and surrounding-whitespace
values for both identity fields.

Created `tests/test_character_config.py`. Verification result:

```text
.venv/bin/python -m pytest tests/test_character_config.py -v
9 passed
```

# 2.5 --- Voice Engine Validation and Fast Unit Tests

`VoiceEngine` now rejects empty/non-string text and voice values, invalid
output-path types, fileless paths, and existing directory paths. The Kokoro
adapter additionally requires a `.wav` output path and converts provider or
audio-writing failures into `VoiceSynthesisError` with the voice and output
path in the error message.

`KokoroVoiceEngine` accepts an optional injected pipeline for fast tests.
`tests/test_voice_engine_validation.py` uses a fake pipeline to cover a
successful write, invalid requests before a provider call, invalid output
extensions, and wrapped provider failures.

Verification result:

```text
.venv/bin/python -m pytest tests/test_voice_engine_validation.py tests/test_voice_engine.py -v
11 passed, 5 warnings
```

# 3.1 --- Versioned Project, Character, and Asset Model

Implemented `app/project.py` with schema-version 1 project configuration,
legacy version-0 upgrades, render defaults, reusable asset definitions, and
safe asset resolution. Assets must be relative to the configured asset root;
missing files and incompatible file types produce clear errors.

Expanded `CharacterConfig` with optional visual asset references and
deterministic animation defaults. Added `SceneConfig` and `CameraConfig`.

Created reusable SVG starter assets under `assets/` and a validated example
configuration at `projects/starter-project/project.json`.

Verification result:

```text
.venv/bin/python -m pytest tests/test_character_config.py tests/test_project_model.py -v
18 passed
```

# Script Format and Dialogue Timeline

Implemented a schema-version 1 JSON script format, documented in
`app/script/FORMAT.md`, and added a matching `script.json` to the starter
project. Scripts support dialogue, actions, ambience, sound effects, and
captions.

`DialogueTimelineBuilder` validates scene and speaker references against the
project, synthesizes dialogue through the provider-neutral `VoiceEngine`,
reads the WAV duration, and generates sequential timestamped timeline events.
The same dialogue interval now supplies the future animation, audio, and
caption stages with a common timing contract.

Verification result:

```text
.venv/bin/python -m pytest tests/test_script_parser.py tests/test_dialogue_timeline.py -v
10 passed
```

# Next Planned Step --- Deterministic 2D Animation and Scene Rendering

Render the starter scene and character as deterministic frames, with simple
dialogue-timed mouth animation. This begins the visual path to a full MP4.

# Working Principles Going Forward

1.  Plan before implementing.
2.  Build the deterministic 2D system first.
3.  Use AI to assist the pipeline, not replace its foundations.
4.  Keep character assets reusable for consistency.
5.  Keep TTS engines swappable behind an interface.
6.  Use stable voice IDs for persistent character voices.
7.  Keep generated media out of Git.
8.  Commit meaningful completed checkpoints.
9.  Introduce branches when they solve a real workflow problem.
10. Do not require Docker without a concrete reason.
11. Prefer local-first components compatible with the available
    CPU-focused hardware.
12. Treat third-party warnings separately from failures in AL Studio
    code.
13. Discuss architectural changes explicitly rather than casually
    changing agreed structure.
14. Keep this progress document updated as implementation advances.
