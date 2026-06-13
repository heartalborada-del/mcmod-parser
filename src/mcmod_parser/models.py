"""Unified data models for mod metadata."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class LoaderType(Enum):
    """Supported mod loader types."""
    FORGE = "forge"
    NEOFORGE = "neoforge"
    FABRIC = "fabric"
    QUILT = "quilt"
    UNKNOWN = "unknown"


class Authors:
    """Normalized authors representation.

    Forge stores authors as a simple string.
    Fabric stores authors as a list of strings or list of {name, contact} objects.
    Quilt stores contributors as a dict of {name: role}.
    This class normalizes all formats while preserving the original data.
    """

    __slots__ = ("names", "raw")

    def __init__(self, raw: Any = None):
        self.raw = raw
        self.names: list[str] = self._extract_names(raw)

    @staticmethod
    def _extract_names(raw: Any) -> list[str]:
        """Extract author names from various formats into a flat list."""
        if raw is None:
            return []
        if isinstance(raw, str):
            # Forge-style: comma-separated or single string
            return [n.strip() for n in raw.split(",") if n.strip()]
        if isinstance(raw, list):
            names: list[str] = []
            for item in raw:
                if isinstance(item, str):
                    names.append(item)
                elif isinstance(item, dict):
                    # Fabric {name, contact} format
                    name = item.get("name", "")
                    if name:
                        names.append(name)
            return names
        if isinstance(raw, dict):
            # Quilt-style {name: role}
            return list(raw.keys())
        return [str(raw)]

    def __repr__(self) -> str:
        return f"Authors({self.names!r})"

    def __str__(self) -> str:
        return ", ".join(self.names)

    def __eq__(self, other: object) -> bool:
        if isinstance(other, Authors):
            return self.names == other.names
        return NotImplemented


@dataclass
class DependencyInfo:
    """A single dependency declaration."""
    mod_id: str
    mandatory: bool = True
    version_range: str = ""
    side: str = ""  # BOTH, CLIENT, SERVER
    ordering: str = ""  # BEFORE, AFTER (Forge only)
    kind: str = "depends"  # depends, recommends, suggests, breaks, conflicts


@dataclass
class ModInfo:
    """Unified mod metadata model.

    All fields are normalized from their loader-specific formats
    into a consistent representation.
    """

    mod_id: str
    """Unique mod identifier (lowercase alphanumeric with hyphens/underscores)."""

    version: str
    """Mod version string."""

    loader_type: LoaderType = LoaderType.UNKNOWN
    """Which mod loader this metadata came from."""

    display_name: str = ""
    """Human-readable mod name."""

    description: str = ""
    """Mod description text."""

    authors: Authors = field(default_factory=Authors)
    """Mod authors/contributors."""

    license: str = ""
    """License name or identifier."""

    dependencies: list[DependencyInfo] = field(default_factory=list)
    """Declared dependencies."""

    raw: dict[str, Any] | None = None
    """Raw parsed metadata for advanced use."""

    def __repr__(self) -> str:
        return (
            f"ModInfo(mod_id={self.mod_id!r}, version={self.version!r}, "
            f"loader={self.loader_type.value})"
        )

    def to_json_dict(self) -> dict[str, Any]:
        """Serialize to a JSON-serializable dictionary."""
        return {
            "mod_id": self.mod_id,
            "version": self.version,
            "loader_type": self.loader_type.value,
            "display_name": self.display_name,
            "description": self.description,
            "authors": self.authors.names,
            "license": self.license,
            "dependencies": [
                {
                    "mod_id": d.mod_id,
                    "mandatory": d.mandatory,
                    "version_range": d.version_range,
                    "side": d.side,
                    "ordering": d.ordering,
                    "kind": d.kind,
                }
                for d in self.dependencies
            ],
        }
