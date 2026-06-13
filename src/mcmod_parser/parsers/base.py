"""Abstract base class for mod metadata parsers."""

from __future__ import annotations

from abc import ABC, abstractmethod

from mcmod_parser.models import LoaderType, ModInfo


class BaseParser(ABC):
    """Abstract parser for a specific mod metadata format."""

    loader_type: LoaderType

    @abstractmethod
    def parse(self, content: str) -> list[ModInfo]:
        """Parse raw metadata content into a list of ModInfo objects.

        Args:
            content: The raw file content as a string.

        Returns:
            A list of ModInfo instances. Forge can have multiple [[mods]] in one file.
        """
        ...

    @staticmethod
    def detect_loader(filename: str, content: str | None = None) -> LoaderType:
        """Detect the loader type from a metadata filename and optional content.

        Detection priority:
        1. quilt.mod.json → QUILT
        2. fabric.mod.json → FABRIC
        3. neoforge.mods.toml → NEOFORGE
        4. mods.toml → FORGE (default for TOML files)

        Args:
            filename: The metadata file name (e.g. 'mods.toml', 'fabric.mod.json').
            content: Optional file content for deeper inspection.

        Returns:
            The detected LoaderType.
        """
        basename = filename.rsplit("/", 1)[-1].rsplit("\\", 1)[-1]

        if basename == "quilt.mod.json":
            return LoaderType.QUILT
        if basename == "fabric.mod.json":
            return LoaderType.FABRIC
        if basename == "neoforge.mods.toml":
            return LoaderType.NEOFORGE
        if basename == "mods.toml":
            # Could be Forge or NeoForge — check content for modLoader field
            if content and 'modLoader' in content:
                return LoaderType.NEOFORGE
            return LoaderType.FORGE

        return LoaderType.UNKNOWN
