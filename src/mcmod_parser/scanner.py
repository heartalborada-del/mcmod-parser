"""Directory scanner — batch-parses mod JARs and metadata files."""

from __future__ import annotations

import json
from pathlib import Path

from mcmod_parser.jar_reader import parse_jar
from mcmod_parser.models import LoaderType, ModInfo
from mcmod_parser.parsers.base import BaseParser
from mcmod_parser.parsers.fabric import FabricParser
from mcmod_parser.parsers.forge import ForgeParser
from mcmod_parser.parsers.quilt import QuiltParser


def parse_metadata_file(file_path: str | Path) -> list[ModInfo]:
    """Parse a raw metadata file (.toml or .json) directly.

    Args:
        file_path: Path to a mods.toml, fabric.mod.json, or quilt.mod.json file.

    Returns:
        List of parsed ModInfo objects.
    """
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    filename = path.name

    loader_type = BaseParser.detect_loader(filename, content)

    if loader_type == LoaderType.QUILT:
        return QuiltParser().parse(content)
    elif loader_type == LoaderType.FABRIC:
        return FabricParser().parse(content)
    elif loader_type in (LoaderType.FORGE, LoaderType.NEOFORGE):
        parser = ForgeParser(loader_type)
        return parser.parse(content)
    else:
        # Try all parsers heuristically
        # Try JSON first
        try:
            data = json.loads(content)
            if "quilt_loader" in data:
                return QuiltParser().parse(content)
            if "id" in data or "schemaVersion" in data:
                return FabricParser().parse(content)
        except (json.JSONDecodeError, ValueError):
            pass
        # Try TOML
        try:
            return ForgeParser().parse(content)
        except Exception:
            pass

    return []


def scan_directory(
    directory: str | Path,
    *,
    recursive: bool = False,
    filter_loader: LoaderType | None = None,
) -> list[ModInfo]:
    """Scan a directory for mod JARs and metadata files, parse all.

    Args:
        directory: Path to the directory to scan.
        recursive: If True, scan subdirectories recursively.
        filter_loader: If set, only return mods of the specified loader type.

    Returns:
        Flat list of all parsed ModInfo objects.
    """
    dir_path = Path(directory)
    if not dir_path.is_dir():
        raise NotADirectoryError(f"Not a directory: {directory}")

    # Collect files
    glob_pattern = "**/*" if recursive else "*"
    all_items = list(dir_path.glob(glob_pattern))

    results: list[ModInfo] = []

    for item in all_items:
        if not item.is_file():
            continue

        suffix = item.suffix.lower()
        name = item.name.lower()

        try:
            if suffix == ".jar":
                mods = parse_jar(item)
            elif name in (
                "mods.toml",
                "neoforge.mods.toml",
                "fabric.mod.json",
                "quilt.mod.json",
            ):
                mods = parse_metadata_file(item)
            elif suffix in (".toml", ".json"):
                # Could be a renamed metadata file
                mods = parse_metadata_file(item)
                if not mods:
                    continue
            else:
                continue

            for mod in mods:
                if filter_loader and mod.loader_type != filter_loader:
                    continue
                results.append(mod)
        except Exception:
            # Skip unparseable files silently
            continue

    return results
