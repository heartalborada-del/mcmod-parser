"""Parser for Quilt mod metadata (quilt.mod.json)."""

from __future__ import annotations

import json
from typing import Any

from mcmod_parser.models import Authors, DependencyInfo, LoaderType, ModInfo
from mcmod_parser.parsers.base import BaseParser


class QuiltParser(BaseParser):
    """Parser for Quilt ``quilt.mod.json`` metadata files.

    Quilt nests everything under a ``quilt_loader`` object, with
    display metadata further nested under ``quilt_loader.metadata``.
    """

    loader_type = LoaderType.QUILT

    def parse(self, content: str) -> list[ModInfo]:
        """Parse Quilt JSON content.

        Args:
            content: Raw JSON string from quilt.mod.json.

        Returns:
            Single-element list containing the parsed ModInfo.
        """
        try:
            data: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError:
            return []

        loader: dict[str, Any] = data.get("quilt_loader", {})
        if not loader:
            return []

        mod_id = loader.get("id", "")
        version = loader.get("version", "")
        if not mod_id or not version:
            return []

        metadata: dict[str, Any] = loader.get("metadata", {})

        display_name = metadata.get("name", "")
        description = metadata.get("description", "")

        # Contributors: dict of {name: role}
        contributors_raw = metadata.get("contributors", {})
        authors = Authors(contributors_raw)

        # License: str, list[str]
        license_raw = metadata.get("license", "")
        if isinstance(license_raw, list):
            license_str = ", ".join(str(l) for l in license_raw)
        else:
            license_str = str(license_raw) if license_raw else ""

        # Dependencies: list of {id, versions, reason, optional}
        deps: list[DependencyInfo] = []
        depends_list: list[dict[str, Any]] = loader.get("depends", [])
        for dep in depends_list:
            dep_id = dep.get("id", "")
            if not dep_id:
                continue
            deps.append(DependencyInfo(
                mod_id=dep_id,
                mandatory=not dep.get("optional", False),
                version_range=str(dep.get("versions", "")),
                kind="depends",
            ))

        return [ModInfo(
            mod_id=mod_id,
            version=version,
            loader_type=LoaderType.QUILT,
            display_name=display_name,
            description=description,
            authors=authors,
            license=license_str,
            dependencies=deps,
            raw=loader,
        )]
