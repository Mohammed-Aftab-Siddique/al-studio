"""Provider-neutral character configuration."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CharacterConfig:
    """Persistent identity settings required for a character.

    ``voice_id`` is intentionally an opaque value owned by the selected
    voice provider. Character code stores and forwards it, but does not
    import, configure, or otherwise depend on a provider implementation.
    """

    name: str
    voice_id: str

    def __post_init__(self) -> None:
        self._validate_field("name", self.name)
        self._validate_field("voice_id", self.voice_id)

    @staticmethod
    def _validate_field(field_name: str, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")
        if value != value.strip():
            raise ValueError(f"{field_name} must not have leading or trailing whitespace")
