"""mcmod-parser: Parse Minecraft mod metadata from Forge/NeoForge/Fabric/Quilt JARs."""

from mcmod_parser.models import ModInfo, LoaderType, Authors
from mcmod_parser.jar_reader import parse_jar
from mcmod_parser.scanner import scan_directory, parse_metadata_file

__all__ = [
    "ModInfo",
    "LoaderType",
    "Authors",
    "parse_jar",
    "scan_directory",
    "parse_metadata_file",
]
__version__ = "0.1.0"
