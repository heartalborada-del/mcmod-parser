"""Tests for Fabric JSON parser."""

from mcmod_parser.models import LoaderType
from mcmod_parser.parsers.fabric import FabricParser

FABRIC_BASIC = """{
  "schemaVersion": 1,
  "id": "examplemod",
  "version": "1.0.0",
  "name": "Example Mod",
  "description": "A test Fabric mod.",
  "authors": ["Alice", "Bob"],
  "license": "MIT"
}"""

FABRIC_AUTHORS_DICT = """{
  "schemaVersion": 1,
  "id": "testmod",
  "version": "2.0",
  "authors": [
    {"name": "Alice", "contact": "alice@example.com"},
    {"name": "Bob"}
  ]
}"""

FABRIC_LICENSE_LIST = """{
  "schemaVersion": 1,
  "id": "licensedmod",
  "version": "1.0",
  "license": ["MIT", "CC-BY-4.0"]
}"""

FABRIC_WITH_DEPS = """{
  "schemaVersion": 1,
  "id": "depmod",
  "version": "3.0",
  "depends": {
    "minecraft": ">=1.20",
    "fabricloader": ">=0.15.0"
  },
  "recommends": {
    "modmenu": "*"
  },
  "conflicts": {
    "badmod": "*"
  }
}"""

FABRIC_MINIMAL = """{
  "schemaVersion": 1,
  "id": "mini",
  "version": "0.1"
}"""


class TestFabricParser:
    def test_parse_basic(self) -> None:
        parser = FabricParser()
        results = parser.parse(FABRIC_BASIC)
        assert len(results) == 1
        mod = results[0]
        assert mod.mod_id == "examplemod"
        assert mod.version == "1.0.0"
        assert mod.display_name == "Example Mod"
        assert mod.description == "A test Fabric mod."
        assert mod.authors.names == ["Alice", "Bob"]
        assert mod.license == "MIT"
        assert mod.loader_type == LoaderType.FABRIC

    def test_parse_empty_returns_empty(self) -> None:
        parser = FabricParser()
        results = parser.parse("{}")
        assert results == []

    def test_parse_authors_as_dicts(self) -> None:
        parser = FabricParser()
        results = parser.parse(FABRIC_AUTHORS_DICT)
        assert len(results) == 1
        assert results[0].authors.names == ["Alice", "Bob"]

    def test_parse_license_list(self) -> None:
        parser = FabricParser()
        results = parser.parse(FABRIC_LICENSE_LIST)
        assert len(results) == 1
        assert results[0].license == "MIT, CC-BY-4.0"

    def test_parse_dependencies(self) -> None:
        parser = FabricParser()
        results = parser.parse(FABRIC_WITH_DEPS)
        assert len(results) == 1
        mod = results[0]
        # depends + recommends + conflicts
        assert len(mod.dependencies) == 4
        dep_ids = {d.mod_id for d in mod.dependencies}
        assert dep_ids == {"minecraft", "fabricloader", "modmenu", "badmod"}

        # Check mandatory flag
        minecraft_dep = next(d for d in mod.dependencies if d.mod_id == "minecraft")
        assert minecraft_dep.mandatory is True

        modmenu_dep = next(d for d in mod.dependencies if d.mod_id == "modmenu")
        assert modmenu_dep.mandatory is False
        assert modmenu_dep.kind == "recommends"

    def test_parse_minimal(self) -> None:
        parser = FabricParser()
        results = parser.parse(FABRIC_MINIMAL)
        assert len(results) == 1
        mod = results[0]
        assert mod.mod_id == "mini"
        assert mod.version == "0.1"
        assert mod.display_name == ""
        assert mod.description == ""
        assert mod.authors.names == []
        assert mod.license == ""
