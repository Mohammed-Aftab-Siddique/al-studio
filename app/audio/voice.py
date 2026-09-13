from abc import ABC, abstractmethod
from pathlib import Path


class VoiceSynthesisError(RuntimeError):
    """Raised when a voice provider cannot synthesize requested speech."""


class VoiceEngine(ABC):
    """Interface for text-to-speech engines."""

    @staticmethod
    def validate_synthesis_request(
        text: str,
        voice: str,
        output_path: Path,
    ) -> None:
        """Validate provider-neutral synthesis inputs."""
        VoiceEngine._validate_nonempty_string("text", text)
        VoiceEngine._validate_nonempty_string("voice", voice)

        if not isinstance(output_path, Path):
            raise TypeError("output_path must be a pathlib.Path")
        if not output_path.name:
            raise ValueError("output_path must name a file")
        if output_path.exists() and output_path.is_dir():
            raise ValueError("output_path must not be an existing directory")

    @staticmethod
    def _validate_nonempty_string(field_name: str, value: str) -> None:
        if not isinstance(value, str):
            raise TypeError(f"{field_name} must be a string")
        if not value.strip():
            raise ValueError(f"{field_name} must not be empty")

    @abstractmethod
    def synthesize(
        self,
        text: str,
        voice: str,
        output_path: Path,
    ) -> Path:
        """Convert text to speech and save it to output_path."""
        raise NotImplementedError
