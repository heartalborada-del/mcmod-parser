"""Parser for Fabric mod metadata (fabric.mod.json)."""

from __future__ import annotations

import json
from typing import Any

from mcmod_parser.models import Authors, DependencyInfo, LoaderType, ModInfo
from mcmod_parser.parsers.base import BaseParser


class FabricParser(BaseParser):
    """Parser for Fabric ``fabric.mod.json`` metadata files."""

    loader_type = LoaderType.FABRIC

    def parse(self, content: str) -> list[ModInfo]:
        """Parse Fabric JSON content.

        Args:
            content: Raw JSON string from fabric.mod.json.

        Returns:
            Single-element list containing the parsed ModInfo.
        """
        try:
            data: dict[str, Any] = json.loads(content)
        except json.JSONDecodeError:
            return []

        mod_id = data.get("id", "")
        version = data.get("version", "")
        if not mod_id or not version:
            return []

        display_name = data.get("name", "")
        description = data.get("description", "")

        # Authors: can be list[str], list[{name, contact}], or string
        authors_raw = data.get("authors", [])
        authors = Authors(authors_raw)

        # License: can be str, list[str]
        license_raw = data.get("license", "")
        if isinstance(license_raw, list):
            license_str = ", ".join(str(l) for l in license_raw)
        else:
            license_str = str(license_raw) if license_raw else ""

        # Parse dependencies from depends/recommends/suggests/breaks/conflicts
        deps: list[DependencyInfo] = []
        for kind in ("depends", "recommends", "suggests", "breaks", "conflicts"):
            dep_map: dict[str, str] | list[dict[str, str]] = data.get(kind, {})
            if isinstance(dep_map, dict):
                for dep_id, ver_range in dep_map.items():
                    deps.append(DependencyInfo(
                        mod_id=dep_id,
                        mandatory=(kind == "depends"),
                        version_range=str(ver_range),
                        kind=kind,
                    ))
            elif isinstance(dep_map, list):
                for item in dep_map:
                    if isinstance(item, dict):
                        deps.append(DependencyInfo(
                            mod_id=item.get("id", ""),
                            mandatory=(kind == "depends"),
                            version_range=item.get("versions", ""),
                            kind=kind,
                        ))

        return [ModInfo(
            mod_id=mod_id,
            version=version,
            loader_type=LoaderType.FABRIC,
            display_name=display_name,
            description=description,
            authors=authors,
            license=license_str,
            dependencies=deps,
            raw=data,
        )]
