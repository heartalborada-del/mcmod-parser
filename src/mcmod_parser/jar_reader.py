"""JAR file reader — extracts mod metadata from Minecraft mod JARs.

JAR files are just ZIP files. This module opens them and routes
the metadata file to the appropriate parser.
"""

from __future__ import annotations

import re
import zipfile
from pathlib import Path
from typing import BinaryIO

from mcmod_parser.models import LoaderType, ModInfo
from mcmod_parser.parsers.base import BaseParser
from mcmod_parser.parsers.fabric import FabricParser
from mcmod_parser.parsers.forge import ForgeParser
from mcmod_parser.parsers.quilt import QuiltParser

# Detection priority: check specific filenames first
_METADATA_CANDIDATES = [
    ("quilt.mod.json", QuiltParser()),
    ("fabric.mod.json", FabricParser()),
    ("META-INF/neoforge.mods.toml", ForgeParser()),
    ("META-INF/mods.toml", ForgeParser()),
]

# Matches unresolved Gradle/Maven placeholders like ${file.jarVersion} or ${version}
_PLACEHOLDER_RE = re.compile(r"^\$\{[^}]+\}$")

# Matches a semver-like version segment in a filename:
#   X.Y.Z[-pre.1][+build.2]
# The negative lookahead (?!\d+\.\d) prevents consuming a "-" that
# precedes a *separate* version number (e.g. "1.20.1-1.0.0" → two
# separate matches, not "1.20.1-1.0.0" as one version).
_SEMVER_RE = re.compile(
    r"\d+\.\d+(?:\.\d+)*"                                     # major.minor(.patch)*
    r"(?:-(?!\d+\.\d)[a-zA-Z0-9]+(?:\.[a-zA-Z0-9]+)*)*"       # -prerelease
    r"(?:\+[a-zA-Z0-9.]+)?"                                    # +build
)


def _read_jar_entry(jar: zipfile.ZipFile, entry_name: str) -> str:
    """Read a text entry from a JAR file, decoding as UTF-8."""
    return jar.read(entry_name).decode("utf-8")


def _is_placeholder_version(version: str) -> bool:
    """Check whether a version string is an unresolved build placeholder.

    Examples: ``${file.jarVersion}``, ``${version}``.
    """
    return bool(_PLACEHOLDER_RE.match(version))


def _extract_version_from_filename(jar_path: Path) -> str | None:
    """Attempt to extract a version from a JAR filename.

    Uses a semver regex to find all version-like patterns and returns
    the *last* one (the mod version, as opposed to an MC version prefix).

    Handles patterns including:
    - ``modname-1.2.3.jar`` → ``1.2.3``
    - ``modname-1.2.3-1.20.1.jar`` → ``1.2.3``
    - ``modname-1.2.3-build.4.jar`` → ``1.2.3-build.4``
    - ``modname-1.2.3-alpha.1+build.2.jar`` → ``1.2.3-alpha.1+build.2``

    Returns:
        The extracted version string, or None if no plausible version found.
    """
    stem = jar_path.stem  # filename without .jar
    matches = _SEMVER_RE.findall(stem)
    if not matches:
        return None
    # Last version-like pattern is usually the mod version
    # (in modname-1.20.1-1.2.3, the last match 1.2.3 is the mod version)
    return matches[-1]


def _apply_version_fallback(mods: list[ModInfo], jar_path: Path) -> list[ModInfo]:
    """Replace placeholder versions by extracting the real version from
    the JAR filename (e.g. ``modname-1.2.3.jar`` → ``1.2.3``).

    Only modifies entries whose version looks like an unresolved build
    placeholder (``${...}``).
    """
    fallback: str | None = None
    for mod in mods:
        if _is_placeholder_version(mod.version):
            if fallback is None:
                fallback = _extract_version_from_filename(jar_path)
            if fallback:
                mod.version = fallback
    return mods


def parse_jar(jar_path: str | Path) -> list[ModInfo]:
    """Parse a Minecraft mod JAR file and extract mod metadata.

    Detects the mod loader by looking for known metadata files inside
    the JAR. Supports Forge/NeoForge (mods.toml), Fabric (fabric.mod.json),
    and Quilt (quilt.mod.json).

    When the version field contains an unresolved Gradle placeholder
    (``${file.jarVersion}``), the version is extracted from the JAR
    filename instead.

    Args:
        jar_path: Path to a ``.jar`` file.

    Returns:
        List of ModInfo objects. Forge JARs may contain multiple mods.

    Raises:
        FileNotFoundError: If the JAR file does not exist.
        zipfile.BadZipFile: If the file is not a valid ZIP/JAR.
    """
    path = Path(jar_path)
    if not path.is_file():
        raise FileNotFoundError(f"JAR file not found: {jar_path}")

    with zipfile.ZipFile(path, "r") as jar:
        for entry_name, parser in _METADATA_CANDIDATES:
            try:
                content = _read_jar_entry(jar, entry_name)
            except KeyError:
                continue

            # For mods.toml, detect whether it's NeoForge
            loader_type = BaseParser.detect_loader(entry_name, content)
            if isinstance(parser, ForgeParser):
                parser.loader_type = loader_type

            return _apply_version_fallback(parser.parse(content), path)

    # No metadata file found — try a brute-force search
    for name in jar.namelist():
        basename = name.rsplit("/", 1)[-1]
        loader_type = BaseParser.detect_loader(basename)
        if loader_type == LoaderType.FABRIC or loader_type == LoaderType.QUILT:
            parser = QuiltParser() if loader_type == LoaderType.QUILT else FabricParser()
            content = _read_jar_entry(jar, name)
            return _apply_version_fallback(parser.parse(content), path)
        if loader_type in (LoaderType.FORGE, LoaderType.NEOFORGE):
            parser = ForgeParser(loader_type)
            content = _read_jar_entry(jar, name)
            return _apply_version_fallback(parser.parse(content), path)

    return []
