"""Tests for JAR file reader and loader detection."""

import io
import zipfile

from mcmod_parser.models import LoaderType
from mcmod_parser.parsers.base import BaseParser


class TestDetectLoader:
    def test_detect_quilt(self) -> None:
        assert BaseParser.detect_loader("quilt.mod.json") == LoaderType.QUILT

    def test_detect_fabric(self) -> None:
        assert BaseParser.detect_loader("fabric.mod.json") == LoaderType.FABRIC

    def test_detect_neoforge_explicit(self) -> None:
        assert BaseParser.detect_loader("neoforge.mods.toml") == LoaderType.NEOFORGE

    def test_detect_forge_default(self) -> None:
        assert BaseParser.detect_loader("mods.toml") == LoaderType.FORGE

    def test_detect_neoforge_from_content(self) -> None:
        result = BaseParser.detect_loader(
            "mods.toml",
            content='modLoader = "javafml"\n[[mods]]\nmodId="test"\nversion="1.0"'
        )
        assert result == LoaderType.NEOFORGE

    def test_detect_unknown(self) -> None:
        assert BaseParser.detect_loader("unknown.file") == LoaderType.UNKNOWN

    def test_detect_with_path_prefix(self) -> None:
        assert BaseParser.detect_loader("META-INF/mods.toml") == LoaderType.FORGE
        assert BaseParser.detect_loader("META-INF\\neoforge.mods.toml") == LoaderType.NEOFORGE


def _make_jar(entries: dict[str, str]) -> bytes:
    """Create an in-memory JAR/ZIP with the given text entries."""
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for name, content in entries.items():
            zf.writestr(name, content)
    return buf.getvalue()


class TestParseJar:
    def test_fabric_jar(self, tmp_path) -> None:
        from mcmod_parser.jar_reader import parse_jar

        jar_data = _make_jar({
            "fabric.mod.json": """{
                "schemaVersion": 1,
                "id": "fabricmod",
                "version": "1.0.0",
                "name": "Fabric Mod"
            }"""
        })
        jar_path = tmp_path / "fabricmod.jar"
        jar_path.write_bytes(jar_data)

        results = parse_jar(jar_path)
        assert len(results) == 1
        assert results[0].mod_id == "fabricmod"
        assert results[0].loader_type == LoaderType.FABRIC

    def test_forge_jar(self, tmp_path) -> None:
        from mcmod_parser.jar_reader import parse_jar

        jar_data = _make_jar({
            "META-INF/mods.toml": """\
license = "MIT"
[[mods]]
modId = "forgemod"
version = "2.0"
displayName = "Forge Mod"
"""
        })
        jar_path = tmp_path / "forgemod.jar"
        jar_path.write_bytes(jar_data)

        results = parse_jar(jar_path)
        assert len(results) == 1
        assert results[0].mod_id == "forgemod"
        assert results[0].loader_type == LoaderType.FORGE

    def test_quilt_jar(self, tmp_path) -> None:
        from mcmod_parser.jar_reader import parse_jar

        jar_data = _make_jar({
            "quilt.mod.json": """{
                "schema_version": 1,
                "quilt_loader": {
                    "id": "quiltmod",
                    "version": "3.0",
                    "metadata": {"name": "Quilt Mod"}
                }
            }"""
        })
        jar_path = tmp_path / "quiltmod.jar"
        jar_path.write_bytes(jar_data)

        results = parse_jar(jar_path)
        assert len(results) == 1
        assert results[0].mod_id == "quiltmod"
        assert results[0].loader_type == LoaderType.QUILT

    def test_quilt_priority_over_fabric(self, tmp_path) -> None:
        """Quilt JARs may contain both quilt.mod.json and fabric.mod.json.
        quilt.mod.json should take priority."""
        from mcmod_parser.jar_reader import parse_jar

        jar_data = _make_jar({
            "quilt.mod.json": """{
                "schema_version": 1,
                "quilt_loader": {
                    "id": "quiltmod",
                    "version": "1.0"
                }
            }""",
            "fabric.mod.json": """{
                "schemaVersion": 1,
                "id": "fabricmod",
                "version": "2.0"
            }"""
        })
        jar_path = tmp_path / "hybrid.jar"
        jar_path.write_bytes(jar_data)

        results = parse_jar(jar_path)
        assert len(results) == 1
        assert results[0].mod_id == "quiltmod"

    def test_missing_metadata(self, tmp_path) -> None:
        from mcmod_parser.jar_reader import parse_jar

        jar_data = _make_jar({"META-INF/MANIFEST.MF": "Manifest-Version: 1.0"})
        jar_path = tmp_path / "empty.jar"
        jar_path.write_bytes(jar_data)

        results = parse_jar(jar_path)
        assert results == []

    def test_file_not_found(self) -> None:
        from mcmod_parser.jar_reader import parse_jar
        import pytest
        with pytest.raises(FileNotFoundError):
            parse_jar("/nonexistent/file.jar")


class TestVersionFallback:
    def test_is_placeholder_true(self) -> None:
        from mcmod_parser.jar_reader import _is_placeholder_version
        assert _is_placeholder_version("${file.jarVersion}") is True
        assert _is_placeholder_version("${version}") is True
        assert _is_placeholder_version("${mod_version}") is True

    def test_is_placeholder_false(self) -> None:
        from mcmod_parser.jar_reader import _is_placeholder_version
        assert _is_placeholder_version("1.0.0") is False
        assert _is_placeholder_version("1.2.3-build.4") is False
        assert _is_placeholder_version("") is False
        assert _is_placeholder_version("not a placeholder ${either}") is False

    def test_extract_version_simple(self) -> None:
        from mcmod_parser.jar_reader import _extract_version_from_filename
        from pathlib import Path
        assert _extract_version_from_filename(Path("modname-1.2.3.jar")) == "1.2.3"

    def test_extract_version_with_mc_version(self) -> None:
        from mcmod_parser.jar_reader import _extract_version_from_filename
        from pathlib import Path
        # constructionstick-1.21.1-1.0.0.jar → mod version is 1.0.0
        assert _extract_version_from_filename(
            Path("constructionstick-1.21.1-1.0.0.jar")
        ) == "1.0.0"

    def test_extract_version_with_build_suffix(self) -> None:
        from mcmod_parser.jar_reader import _extract_version_from_filename
        from pathlib import Path
        assert _extract_version_from_filename(
            Path("modname-1.2.3-build.4.jar")
        ) == "1.2.3-build.4"

    def test_extract_version_no_version(self) -> None:
        from mcmod_parser.jar_reader import _extract_version_from_filename
        from pathlib import Path
        assert _extract_version_from_filename(Path("modname.jar")) is None

    def test_parse_jar_placeholder_fallback(self, tmp_path) -> None:
        """JAR with ${file.jarVersion} should fall back to filename version."""
        from mcmod_parser.jar_reader import parse_jar

        jar_data = _make_jar({
            "META-INF/neoforge.mods.toml": """\
modLoader = "javafml"
[[mods]]
modId = "stickmod"
version = "${file.jarVersion}"
displayName = "Construction Sticks"
"""
        })
        jar_path = tmp_path / "constructionstick-1.21.1-1.0.0.jar"
        jar_path.write_bytes(jar_data)

        results = parse_jar(jar_path)
        assert len(results) == 1
        assert results[0].mod_id == "stickmod"
        assert results[0].version == "1.0.0"  # extracted from filename

    def test_parse_jar_normal_version_unchanged(self, tmp_path) -> None:
        """A normal version should NOT be overwritten by filename fallback."""
        from mcmod_parser.jar_reader import parse_jar

        jar_data = _make_jar({
            "META-INF/mods.toml": """\
license = "MIT"
[[mods]]
modId = "normalmod"
version = "2.5.0"
"""
        })
        jar_path = tmp_path / "normalmod-9.9.9.jar"
        jar_path.write_bytes(jar_data)

        results = parse_jar(jar_path)
        assert len(results) == 1
        assert results[0].version == "2.5.0"  # NOT overwritten to 9.9.9
