"""Tests for directory scanner and metadata file parser."""

import json

from mcmod_parser.models import LoaderType
from mcmod_parser.scanner import parse_metadata_file, scan_directory


class TestParseMetadataFile:
    def test_parse_fabric_json(self, tmp_path) -> None:
        f = tmp_path / "fabric.mod.json"
        f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "testfabric",
            "version": "1.0"
        }))
        results = parse_metadata_file(f)
        assert len(results) == 1
        assert results[0].mod_id == "testfabric"
        assert results[0].loader_type == LoaderType.FABRIC

    def test_parse_quilt_json(self, tmp_path) -> None:
        f = tmp_path / "quilt.mod.json"
        f.write_text(json.dumps({
            "schema_version": 1,
            "quilt_loader": {
                "id": "testquilt",
                "version": "2.0"
            }
        }))
        results = parse_metadata_file(f)
        assert len(results) == 1
        assert results[0].mod_id == "testquilt"
        assert results[0].loader_type == LoaderType.QUILT

    def test_parse_forge_toml(self, tmp_path) -> None:
        f = tmp_path / "mods.toml"
        f.write_text("""\
license = "MIT"
[[mods]]
modId = "testforge"
version = "3.0"
""")
        results = parse_metadata_file(f)
        assert len(results) == 1
        assert results[0].mod_id == "testforge"
        assert results[0].loader_type == LoaderType.FORGE

    def test_parse_unknown_json_fallback(self, tmp_path) -> None:
        """A .json file that is neither fabric nor quilt should be tried heuristically."""
        f = tmp_path / "unknown.json"
        f.write_text(json.dumps({
            "id": "heuristicmod",
            "version": "1.0",
            "name": "Test"
        }))
        results = parse_metadata_file(f)
        # Should detect as fabric (has 'id' field but no 'quilt_loader')
        assert len(results) == 1
        assert results[0].mod_id == "heuristicmod"

    def test_parse_invalid_file(self, tmp_path) -> None:
        f = tmp_path / "bad.json"
        f.write_text("not valid json")
        results = parse_metadata_file(f)
        assert results == []


class TestScanDirectory:
    def test_scan_mixed_mods(self, tmp_path) -> None:
        import io
        import zipfile

        mods_dir = tmp_path / "mods"
        mods_dir.mkdir()

        # Create a fabric JAR
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps({
                "schemaVersion": 1,
                "id": "fabricmod",
                "version": "1.0"
            }))
        (mods_dir / "fabricmod.jar").write_bytes(buf.getvalue())

        # Create a standalone forge TOML
        (mods_dir / "mods.toml").write_text("""\
license = "MIT"
[[mods]]
modId = "standalonemod"
version = "4.0"
""")

        # Non-mod file — should be ignored
        (mods_dir / "readme.txt").write_text("hello")

        results = scan_directory(mods_dir)
        mod_ids = {m.mod_id for m in results}
        assert "fabricmod" in mod_ids
        assert "standalonemod" in mod_ids

    def test_filter_loader(self, tmp_path) -> None:
        mods_dir = tmp_path / "mods2"
        mods_dir.mkdir()

        (mods_dir / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "fabriconly",
            "version": "1.0"
        }))
        (mods_dir / "mods.toml").write_text("""\
license = "MIT"
[[mods]]
modId = "forgeonly"
version = "1.0"
""")

        results = scan_directory(mods_dir, filter_loader=LoaderType.FABRIC)
        assert len(results) == 1
        assert results[0].mod_id == "fabriconly"

    def test_recursive_scan(self, tmp_path) -> None:
        root = tmp_path / "root"
        sub = root / "subdir"
        sub.mkdir(parents=True)

        (sub / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "deepmod",
            "version": "1.0"
        }))

        # Non-recursive should find nothing
        results_flat = scan_directory(root, recursive=False)
        assert len(results_flat) == 0

        # Recursive should find the mod
        results_deep = scan_directory(root, recursive=True)
        assert len(results_deep) == 1
        assert results_deep[0].mod_id == "deepmod"

    def test_not_a_directory(self) -> None:
        import pytest
        with pytest.raises(NotADirectoryError):
            scan_directory("/nonexistent/dir")
