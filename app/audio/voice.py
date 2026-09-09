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
