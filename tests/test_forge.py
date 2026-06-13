"""Tests for Forge/NeoForge TOML parser."""

from mcmod_parser.models import LoaderType
from mcmod_parser.parsers.forge import ForgeParser


FORGE_BASIC = """\
license = "MIT"
loaderVersion = "[37,)"

[[mods]]
modId = "examplemod"
version = "1.0.0"
displayName = "Example Mod"
description = "A test mod for Forge."
authors = "Alice, Bob"
"""

FORGE_MULTI_MODS = """\
license = "All Rights Reserved"
loaderVersion = "[37,)"

[[mods]]
modId = "coremod"
version = "2.0"
displayName = "Core Library"

[[mods]]
modId = "featuremod"
version = "1.5"
displayName = "Feature Addon"
description = "Adds extra features."
"""

FORGE_WITH_DEPS = """\
license = "MIT"

[[mods]]
modId = "dependentmod"
version = "3.0"
displayName = "Dependent Mod"

[[dependencies.dependentmod]]
modId = "minecraft"
mandatory = true
versionRange = "[1.20,)"
ordering = "NONE"
side = "BOTH"

[[dependencies.dependentmod]]
modId = "requiredlib"
mandatory = true
versionRange = ">=2.0"
ordering = "AFTER"
side = "BOTH"
"""

NEOFORGE_BASIC = """\
modLoader = "javafml"
license = "MIT"

[[mods]]
modId = "neomod"
version = "4.2.1"
displayName = "NeoForge Mod"
description = "A NeoForge-specific mod."
"""

FORGE_MINIMAL = """\
license = "MIT"

[[mods]]
modId = "mini"
version = "0.1"
"""


class TestForgeParser:
    def test_parse_basic(self) -> None:
        parser = ForgeParser()
        results = parser.parse(FORGE_BASIC)
        assert len(results) == 1
        mod = results[0]
        assert mod.mod_id == "examplemod"
        assert mod.version == "1.0.0"
        assert mod.display_name == "Example Mod"
        assert mod.description == "A test mod for Forge."
        assert mod.authors.names == ["Alice", "Bob"]
        assert mod.license == "MIT"
        assert mod.loader_type == LoaderType.FORGE

    def test_parse_multi_mods(self) -> None:
        parser = ForgeParser()
        results = parser.parse(FORGE_MULTI_MODS)
        assert len(results) == 2
        assert results[0].mod_id == "coremod"
        assert results[0].version == "2.0"
        assert results[1].mod_id == "featuremod"
        assert results[1].version == "1.5"
        # Both inherit root license
        assert results[0].license == "All Rights Reserved"
        assert results[1].license == "All Rights Reserved"

    def test_parse_dependencies(self) -> None:
        parser = ForgeParser()
        results = parser.parse(FORGE_WITH_DEPS)
        assert len(results) == 1
        mod = results[0]
        assert len(mod.dependencies) == 2
        assert mod.dependencies[0].mod_id == "minecraft"
        assert mod.dependencies[0].mandatory is True
        assert mod.dependencies[1].mod_id == "requiredlib"
        assert mod.dependencies[1].ordering == "AFTER"

    def test_parse_neo_detection(self) -> None:
        parser = ForgeParser()
        results = parser.parse(NEOFORGE_BASIC)
        assert len(results) == 1
        mod = results[0]
        # Should detect neo from modLoader field
        assert mod.mod_id == "neomod"
        assert mod.version == "4.2.1"

    def test_neo_parser_explicit(self) -> None:
        parser = ForgeParser(LoaderType.NEOFORGE)
        results = parser.parse(NEOFORGE_BASIC)
        assert len(results) == 1
        assert results[0].loader_type == LoaderType.NEOFORGE

    def test_minimal(self) -> None:
        parser = ForgeParser()
        results = parser.parse(FORGE_MINIMAL)
        assert len(results) == 1
        mod = results[0]
        assert mod.mod_id == "mini"
        assert mod.version == "0.1"
        assert mod.display_name == ""

    def test_empty_mods(self) -> None:
        parser = ForgeParser()
        results = parser.parse('license = "MIT"\n')
        assert results == []

    def test_parse_missing_modid(self) -> None:
        parser = ForgeParser()
        results = parser.parse('license = "MIT"\n[[mods]]\nversion = "1.0"\n')
        assert results == []

    def test_per_mod_license(self) -> None:
        content = """\
license = "RootLicense"
[[mods]]
modId = "m1"
version = "1.0"
license = "PerModLicense"
"""
        parser = ForgeParser()
        results = parser.parse(content)
        assert results[0].license == "PerModLicense"
