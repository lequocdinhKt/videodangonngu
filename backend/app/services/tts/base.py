from abc import ABC, abstractmethod
from pathlib import Path


class TTSEngine(ABC):
    @property
    @abstractmethod
    def provider_name(self) -> str: ...

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        language: str,
        voice: str,
        output_path: Path,
    ) -> Path: ...
