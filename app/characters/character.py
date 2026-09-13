"""Provider-neutral character configuration."""

from dataclasses import dataclass


def _validate_nonempty_trimmed_string(field_name: str, value: str) -> None:
    if not isinstance(value, str):
        raise TypeError(f"{field_name} must be a string")
    if not value.strip():
        raise ValueError(f"{field_name} must not be empty")
    if value != value.strip():
        raise ValueError(f"{field_name} must not have leading or trailing whitespace")


@dataclass(frozen=True, slots=True)
class AnimationConfig:
    """Deterministic visual defaults for a character."""

    idle_motion: bool = True
    mouth_style: str = "simple"

    def __post_init__(self) -> None:
        if not isinstance(self.idle_motion, bool):
            raise TypeError("idle_motion must be a boolean")
        _validate_nonempty_trimmed_string("mouth_style", self.mouth_style)


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    """Persistent identity settings required for a character.

    ``voice_id`` is intentionally an opaque value owned by the selected
    voice provider. Character code stores and forwards it, but does not
    import, configure, or otherwise depend on a provider implementation.
    """

    name: str
    voice_id: str
    visual_asset_id: str | None = None
    animation: AnimationConfig = AnimationConfig()

    def __post_init__(self) -> None:
        self._validate_field("name", self.name)
        self._validate_field("voice_id", self.voice_id)
        if self.visual_asset_id is not None:
            self._validate_field("visual_asset_id", self.visual_asset_id)
        if not isinstance(self.animation, AnimationConfig):
            raise TypeError("animation must be an AnimationConfig")

    @staticmethod
    def _validate_field(field_name: str, value: str) -> None:
        _validate_nonempty_trimmed_string(field_name, value)
