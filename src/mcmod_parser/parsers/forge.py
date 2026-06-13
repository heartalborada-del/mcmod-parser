"""Parser for Forge / NeoForge mods.toml metadata."""

from __future__ import annotations

import tomllib
from typing import Any

from mcmod_parser.models import Authors, DependencyInfo, LoaderType, ModInfo
from mcmod_parser.parsers.base import BaseParser


class ForgeParser(BaseParser):
    """Parser for Forge/NeoForge TOML metadata files.

    Handles both ``META-INF/mods.toml`` and ``META-INF/neoforge.mods.toml``.

    A single TOML file can declare multiple mods via ``[[mods]]`` array.
    """

    loader_type: LoaderType

    def __init__(self, loader_type: LoaderType = LoaderType.FORGE) -> None:
        self.loader_type = loader_type

    def parse(self, content: str) -> list[ModInfo]:
        """Parse Forge/NeoForge TOML content.

        Args:
            content: Raw TOML string from mods.toml or neoforge.mods.toml.

        Returns:
            List of ModInfo – one per ``[[mods]]`` entry.
        """
        data: dict[str, Any] = tomllib.loads(content)

        root_license = data.get("license", "")
        # Detect loader from content if not explicitly set
        if self.loader_type == LoaderType.FORGE and "modLoader" in data:
            detected_loader = LoaderType.NEOFORGE
        else:
            detected_loader = self.loader_type

        mods_entries: list[dict[str, Any]] = data.get("mods", [])
        if not mods_entries:
            return []

        results: list[ModInfo] = []
        for entry in mods_entries:
            mod_id = entry.get("modId", "")
            version = entry.get("version", "")
            if not mod_id or not version:
                continue

            display_name = entry.get("displayName", "")
            description = entry.get("description", "")
            authors_str = entry.get("authors", "")
            # license per-mod overrides root license
            mod_license = entry.get("license", root_license)

            # Parse dependencies: [[dependencies.<modId>]]
            deps: list[DependencyInfo] = []
            deps_section: dict[str, Any] = data.get("dependencies", {})
            mod_deps: list[dict[str, Any]] = deps_section.get(mod_id, [])
            for dep in mod_deps:
                deps.append(DependencyInfo(
                    mod_id=dep.get("modId", ""),
                    mandatory=dep.get("mandatory", True),
                    version_range=dep.get("versionRange", ""),
                    side=dep.get("side", ""),
                    ordering=dep.get("ordering", ""),
                ))

            results.append(ModInfo(
                mod_id=mod_id,
                version=version,
                loader_type=detected_loader,
                display_name=display_name,
                description=description,
                authors=Authors(authors_str),
                license=mod_license,
                dependencies=deps,
                raw=entry,
            ))

        return results
