"""Parser registry for mod metadata formats."""

from mcmod_parser.parsers.base import BaseParser
from mcmod_parser.parsers.forge import ForgeParser
from mcmod_parser.parsers.fabric import FabricParser
from mcmod_parser.parsers.quilt import QuiltParser

__all__ = [
    "BaseParser",
    "ForgeParser",
    "FabricParser",
    "QuiltParser",
]
