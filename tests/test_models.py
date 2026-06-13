"""Tests for data models."""

import json

from mcmod_parser.models import Authors, DependencyInfo, LoaderType, ModInfo


class TestAuthors:
    def test_from_string_forge_style(self) -> None:
        a = Authors("Alice, Bob, Charlie")
        assert a.names == ["Alice", "Bob", "Charlie"]

    def test_from_list_fabric_style(self) -> None:
        a = Authors(["Alice", "Bob"])
        assert a.names == ["Alice", "Bob"]

    def test_from_list_of_dicts_fabric_style(self) -> None:
        a = Authors([
            {"name": "Alice", "contact": "email@example.com"},
            {"name": "Bob"},
        ])
        assert a.names == ["Alice", "Bob"]

    def test_from_dict_quilt_style(self) -> None:
        a = Authors({"Alice": "Developer", "Bob": "Artist"})
        assert a.names == ["Alice", "Bob"]

    def test_from_none(self) -> None:
        a = Authors(None)
        assert a.names == []

    def test_from_empty(self) -> None:
        a = Authors("")
        assert a.names == []

    def test_str_repr(self) -> None:
        a = Authors(["Alice", "Bob"])
        assert str(a) == "Alice, Bob"

    def test_equality(self) -> None:
        a1 = Authors(["Alice", "Bob"])
        a2 = Authors("Alice, Bob")
        assert a1 == a2


class TestModInfo:
    def test_to_json_dict(self) -> None:
        mod = ModInfo(
            mod_id="examplemod",
            version="1.0.0",
            loader_type=LoaderType.FORGE,
            display_name="Example Mod",
            description="A test mod.",
            authors=Authors("Alice"),
            license="MIT",
        )
        d = mod.to_json_dict()
        assert d["mod_id"] == "examplemod"
        assert d["version"] == "1.0.0"
        assert d["loader_type"] == "forge"
        assert d["authors"] == ["Alice"]
        assert d["license"] == "MIT"

    def test_json_serializable(self) -> None:
        mod = ModInfo(
            mod_id="test",
            version="2.0",
            loader_type=LoaderType.FABRIC,
            display_name="Test",
            authors=Authors(["Alice", "Bob"]),
            dependencies=[
                DependencyInfo(mod_id="minecraft", version_range=">=1.20"),
                DependencyInfo(mod_id="fabricloader", version_range=">=0.15"),
            ],
        )
        # Should not raise
        json.dumps(mod.to_json_dict())


class TestLoaderType:
    def test_values(self) -> None:
        assert LoaderType.FORGE.value == "forge"
        assert LoaderType.NEOFORGE.value == "neoforge"
        assert LoaderType.FABRIC.value == "fabric"
        assert LoaderType.QUILT.value == "quilt"
        assert LoaderType.UNKNOWN.value == "unknown"

    def test_from_value(self) -> None:
        assert LoaderType("forge") == LoaderType.FORGE
        assert LoaderType("fabric") == LoaderType.FABRIC
