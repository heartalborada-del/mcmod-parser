"""Tests for Quilt JSON parser."""

from mcmod_parser.models import LoaderType
from mcmod_parser.parsers.quilt import QuiltParser

QUILT_BASIC = """{
  "schema_version": 1,
  "quilt_loader": {
    "group": "com.example",
    "id": "examplemod",
    "version": "1.0.0",
    "metadata": {
      "name": "Example Quilt Mod",
      "description": "A test Quilt mod.",
      "contributors": {
        "Alice": "Developer",
        "Bob": "Artist"
      },
      "license": "MIT"
    }
  }
}"""

QUILT_WITH_DEPS = """{
  "schema_version": 1,
  "quilt_loader": {
    "id": "depquilt",
    "version": "2.0",
    "metadata": {
      "name": "Dependent Quilt Mod"
    },
    "depends": [
      {"id": "minecraft", "versions": ">=1.20"},
      {"id": "quilt_loader", "versions": ">=0.19"},
      {"id": "optional_lib", "versions": "*", "optional": true}
    ]
  }
}"""

QUILT_MINIMAL = """{
  "schema_version": 1,
  "quilt_loader": {
    "id": "miniquilt",
    "version": "0.1.0"
  }
}"""

QUILT_LICENSE_LIST = """{
  "schema_version": 1,
  "quilt_loader": {
    "id": "multi_license",
    "version": "1.0",
    "metadata": {
      "license": ["MIT", "Apache-2.0"]
    }
  }
}"""


class TestQuiltParser:
    def test_parse_basic(self) -> None:
        parser = QuiltParser()
        results = parser.parse(QUILT_BASIC)
        assert len(results) == 1
        mod = results[0]
        assert mod.mod_id == "examplemod"
        assert mod.version == "1.0.0"
        assert mod.display_name == "Example Quilt Mod"
        assert mod.description == "A test Quilt mod."
        assert mod.authors.names == ["Alice", "Bob"]
        assert mod.license == "MIT"
        assert mod.loader_type == LoaderType.QUILT

    def test_parse_dependencies(self) -> None:
        parser = QuiltParser()
        results = parser.parse(QUILT_WITH_DEPS)
        assert len(results) == 1
        mod = results[0]
        assert len(mod.dependencies) == 3

        dep_ids = {d.mod_id for d in mod.dependencies}
        assert "minecraft" in dep_ids
        assert "quilt_loader" in dep_ids
        assert "optional_lib" in dep_ids

        # Check optional flag
        opt_dep = next(d for d in mod.dependencies if d.mod_id == "optional_lib")
        assert opt_dep.mandatory is False

    def test_parse_minimal(self) -> None:
        parser = QuiltParser()
        results = parser.parse(QUILT_MINIMAL)
        assert len(results) == 1
        mod = results[0]
        assert mod.mod_id == "miniquilt"
        assert mod.version == "0.1.0"
        assert mod.display_name == ""
        assert mod.authors.names == []

    def test_empty_returns_empty(self) -> None:
        parser = QuiltParser()
        results = parser.parse("{}")
        assert results == []

    def test_broken_returns_empty(self) -> None:
        parser = QuiltParser()
        results = parser.parse("not json")
        assert results == []

    def test_missing_modid(self) -> None:
        parser = QuiltParser()
        results = parser.parse('{"schema_version":1,"quilt_loader":{"version":"1.0"}}')
        assert results == []

    def test_missing_version(self) -> None:
        parser = QuiltParser()
        results = parser.parse('{"schema_version":1,"quilt_loader":{"id":"test"}}')
        assert results == []

    def test_license_list(self) -> None:
        parser = QuiltParser()
        results = parser.parse(QUILT_LICENSE_LIST)
        assert len(results) == 1
        assert results[0].license == "MIT, Apache-2.0"
