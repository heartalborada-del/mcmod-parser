"""Tests for CLI commands."""

import io
import json
import zipfile

from click.testing import CliRunner

from mcmod_parser.cli import main


class TestCLIParse:
    def test_parse_toml_file(self, tmp_path) -> None:
        runner = CliRunner()
        f = tmp_path / "mods.toml"
        f.write_text("""\
license = "MIT"
[[mods]]
modId = "clitest"
version = "5.0"
displayName = "CLI Test"
""")
        result = runner.invoke(main, ["parse", str(f)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["mod_id"] == "clitest"

    def test_parse_json_file(self, tmp_path) -> None:
        runner = CliRunner()
        f = tmp_path / "fabric.mod.json"
        f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "fabric_cli",
            "version": "1.0",
            "name": "Fabric CLI Test"
        }))
        result = runner.invoke(main, ["parse", str(f)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["mod_id"] == "fabric_cli"

    def test_parse_jar_file(self, tmp_path) -> None:
        runner = CliRunner()

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as zf:
            zf.writestr("fabric.mod.json", json.dumps({
                "schemaVersion": 1,
                "id": "jar_cli_mod",
                "version": "2.0"
            }))
        jar_path = tmp_path / "test.jar"
        jar_path.write_bytes(buf.getvalue())

        result = runner.invoke(main, ["parse", str(jar_path)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data[0]["mod_id"] == "jar_cli_mod"

    def test_parse_table_output(self, tmp_path) -> None:
        runner = CliRunner()
        f = tmp_path / "mods.toml"
        f.write_text("""\
license = "MIT"
[[mods]]
modId = "tabletest"
version = "1.0"
""")
        result = runner.invoke(main, ["parse", str(f), "--output", "table"])
        assert result.exit_code == 0
        assert "tabletest" in result.output
        assert "1.0" in result.output

    def test_parse_text_output(self, tmp_path) -> None:
        runner = CliRunner()
        f = tmp_path / "mods.toml"
        f.write_text("""\
license = "MIT"
[[mods]]
modId = "texttest"
version = "1.0"
""")
        result = runner.invoke(main, ["parse", str(f), "--output", "text"])
        assert result.exit_code == 0
        assert "texttest" in result.output

    def test_parse_loader_filter(self, tmp_path) -> None:
        runner = CliRunner()
        f = tmp_path / "fabric.mod.json"
        f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "fabric_mod",
            "version": "1.0"
        }))
        result = runner.invoke(main, ["parse", str(f), "--loader", "forge"])
        # Filtering to Forge should exclude the Fabric mod
        data = json.loads(result.output)
        assert data == []

    def test_parse_file_not_found(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["parse", "/nonexistent/file.jar"])
        assert result.exit_code != 0


class TestCLIScan:
    def test_scan_directory(self, tmp_path) -> None:
        runner = CliRunner()
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir()

        (mods_dir / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "scanmod",
            "version": "1.0"
        }))

        result = runner.invoke(main, ["scan", str(mods_dir)])
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["mod_id"] == "scanmod"

    def test_scan_json_output(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["scan", "--help"])
        assert result.exit_code == 0
        assert "--output" in result.output

    def test_scan_table_output(self, tmp_path) -> None:
        runner = CliRunner()
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir()

        (mods_dir / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "table_scan",
            "version": "2.0",
            "name": "Table Scan Mod"
        }))

        result = runner.invoke(main, ["scan", str(mods_dir), "--output", "table"])
        assert result.exit_code == 0
        assert "table_scan" in result.output

    def test_scan_recursive_flag(self, tmp_path) -> None:
        runner = CliRunner()
        root = tmp_path / "root"
        sub = root / "sub"
        sub.mkdir(parents=True)

        (sub / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "deep",
            "version": "1.0"
        }))

        # Without recursive
        result = runner.invoke(main, ["scan", str(root)])
        data = json.loads(result.output)
        assert data == []

        # With recursive
        result = runner.invoke(main, ["scan", str(root), "--recursive"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["mod_id"] == "deep"

    def test_scan_loader_filter(self, tmp_path) -> None:
        runner = CliRunner()
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir()

        (mods_dir / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "fabric_scan",
            "version": "1.0"
        }))
        (mods_dir / "mods.toml").write_text("""\
license = "MIT"
[[mods]]
modId = "forge_scan"
version = "2.0"
""")

        result = runner.invoke(main, ["scan", str(mods_dir), "--loader", "forge"])
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["mod_id"] == "forge_scan"


class TestCLIHelp:
    def test_main_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])
        assert result.exit_code == 0
        assert "parse" in result.output
        assert "scan" in result.output

    def test_version(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])
        assert result.exit_code == 0


class TestCLICsv:
    def test_parse_csv_output(self, tmp_path) -> None:
        runner = CliRunner()
        f = tmp_path / "fabric.mod.json"
        f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "csvmod",
            "version": "1.0",
            "name": "CSV Mod",
            "authors": ["Alice"],
            "license": "MIT",
        }))
        result = runner.invoke(main, ["parse", str(f), "--output", "csv"])
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        assert lines[0].startswith("Loader,ModID,Version")
        assert "csvmod" in result.output
        assert "1.0" in result.output
        assert "CSV Mod" in result.output

    def test_scan_csv_output(self, tmp_path) -> None:
        runner = CliRunner()
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir()
        (mods_dir / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "csvscan",
            "version": "2.0",
        }))
        result = runner.invoke(main, ["scan", str(mods_dir), "--output", "csv"])
        assert result.exit_code == 0
        assert "csvscan" in result.output

    def test_csv_no_mods(self, tmp_path) -> None:
        runner = CliRunner()
        mods_dir = tmp_path / "empty"
        mods_dir.mkdir()
        result = runner.invoke(main, ["scan", str(mods_dir), "--output", "csv"])
        assert result.exit_code == 0


class TestCLIOutputFile:
    def test_parse_output_file(self, tmp_path) -> None:
        runner = CliRunner()
        mod_f = tmp_path / "fabric.mod.json"
        mod_f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "fileout",
            "version": "3.0",
        }))
        out_f = tmp_path / "result.csv"
        result = runner.invoke(main, [
            "parse", str(mod_f),
            "--output", "csv",
            "--output-file", str(out_f),
        ])
        assert result.exit_code == 0
        assert out_f.is_file()
        content = out_f.read_text()
        assert "fileout" in content
        assert "3.0" in content
        assert "Saved to" in result.output

    def test_scan_output_file(self, tmp_path) -> None:
        runner = CliRunner()
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir()
        (mods_dir / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "scanfile",
            "version": "4.0",
        }))
        out_f = tmp_path / "scan_result.json"
        result = runner.invoke(main, [
            "scan", str(mods_dir),
            "--output", "json",
            "--output-file", str(out_f),
        ])
        assert result.exit_code == 0
        assert out_f.is_file()
        data = json.loads(out_f.read_text(encoding="utf-8"))
        assert data[0]["mod_id"] == "scanfile"

    def test_output_file_overwrites(self, tmp_path) -> None:
        runner = CliRunner()
        mods_dir = tmp_path / "mods"
        mods_dir.mkdir()
        (mods_dir / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1,
            "id": "overwrite",
            "version": "5.0",
        }))
        out_f = tmp_path / "out.txt"
        out_f.write_text("old content")
        result = runner.invoke(main, [
            "scan", str(mods_dir),
            "--output", "text",
            "--output-file", str(out_f),
        ])
        assert result.exit_code == 0
        assert "overwrite" in out_f.read_text(encoding="utf-8")

    def test_parse_output_file_json(self, tmp_path) -> None:
        runner = CliRunner()
        mod_f = tmp_path / "fabric.mod.json"
        mod_f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "jsonfile",
            "version": "1.5",
            "name": "JSON File Test",
        }))
        out_f = tmp_path / "result.json"
        result = runner.invoke(main, [
            "parse", str(mod_f),
            "--output", "json",
            "--output-file", str(out_f),
        ])
        assert result.exit_code == 0
        data = json.loads(out_f.read_text(encoding="utf-8"))
        assert data[0]["mod_id"] == "jsonfile"
        assert data[0]["display_name"] == "JSON File Test"


class TestOutputAutoName:
    def test_resolve_none_returns_none(self) -> None:
        from mcmod_parser.cli import _resolve_output_path
        assert _resolve_output_path(None, "json") is None

    def test_resolve_dot_generates_name(self) -> None:
        from pathlib import Path
        from mcmod_parser.cli import _resolve_output_path
        result = _resolve_output_path(".", "csv", source=Path("testmod.jar"))
        assert result is not None
        name = result.name
        assert name.startswith("testmod_")
        assert name.endswith(".csv")

    def test_resolve_directory_generates_name_inside(self) -> None:
        from pathlib import Path
        from mcmod_parser.cli import _resolve_output_path
        result = _resolve_output_path("mydir", "json", source=Path("my.jar"))
        assert result is not None
        assert result.parent.name == "mydir"
        assert result.name.endswith(".json")

    def test_resolve_explicit_path_used_as_is(self) -> None:
        from pathlib import Path
        from mcmod_parser.cli import _resolve_output_path
        result = _resolve_output_path("explicit/path.csv", "table")
        assert result == Path("explicit/path.csv")

    def test_resolve_no_source_default_stem(self) -> None:
        from mcmod_parser.cli import _resolve_output_path
        result = _resolve_output_path(".", "json")
        assert result is not None
        assert result.name.startswith("mcmod_output_")

    def test_cli_output_file_dot_auto_name(self, tmp_path) -> None:
        """-f . triggers auto-name in current dir."""
        runner = CliRunner()
        mod_f = tmp_path / "fabric.mod.json"
        mod_f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "autoname",
            "version": "1.0",
        }))

        # Change to tmp_path so "." resolves there
        import os
        old_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)
            result = runner.invoke(main, [
                "parse", str(mod_f),
                "--output", "csv",
                "--output-file", ".",
            ])
            assert result.exit_code == 0
            assert "Saved to" in result.output
            # A file should have been created in tmp_path
            saved_files = list(tmp_path.glob("*.csv"))
            assert len(saved_files) == 1
            content = saved_files[0].read_text(encoding="utf-8")
            assert "autoname" in content
        finally:
            os.chdir(old_cwd)

    def test_cli_output_file_explicit(self, tmp_path) -> None:
        """-f path/to/file.csv uses the given path."""
        runner = CliRunner()
        mod_f = tmp_path / "fabric.mod.json"
        mod_f.write_text(json.dumps({
            "schemaVersion": 1,
            "id": "explicitpath",
            "version": "2.0",
        }))
        out_f = tmp_path / "sub" / "my.csv"
        out_f.parent.mkdir()

        result = runner.invoke(main, [
            "parse", str(mod_f),
            "--output", "csv",
            "--output-file", str(out_f),
        ])
        assert result.exit_code == 0
        assert out_f.is_file()
        assert "explicitpath" in out_f.read_text(encoding="utf-8")


class TestPreprocessArgv:
    def test_bare_f_becomes_f_dot(self) -> None:
        import sys as _sys
        from mcmod_parser import cli

        _sys.argv = ["mcmod-parser", "scan", "dir", "-f"]
        cli._preprocess_argv()
        assert _sys.argv == ["mcmod-parser", "scan", "dir", "-f", "."]

    def test_f_with_value_unchanged(self) -> None:
        import sys as _sys
        from mcmod_parser import cli

        _sys.argv = ["mcmod-parser", "scan", "dir", "-f", "out.csv"]
        cli._preprocess_argv()
        assert _sys.argv == ["mcmod-parser", "scan", "dir", "-f", "out.csv"]

    def test_bare_output_file_flag(self) -> None:
        import sys as _sys
        from mcmod_parser import cli

        _sys.argv = ["mcmod-parser", "parse", "mod.jar", "--output-file"]
        cli._preprocess_argv()
        assert _sys.argv == ["mcmod-parser", "parse", "mod.jar", "--output-file", "."]

    def test_output_file_with_value_unchanged(self) -> None:
        import sys as _sys
        from mcmod_parser import cli

        _sys.argv = ["mcmod-parser", "parse", "mod.jar", "--output-file", "result.csv"]
        cli._preprocess_argv()
        assert _sys.argv == ["mcmod-parser", "parse", "mod.jar", "--output-file", "result.csv"]

    def test_no_f_option_unchanged(self) -> None:
        import sys as _sys
        from mcmod_parser import cli

        _sys.argv = ["mcmod-parser", "scan", "dir", "-o", "json"]
        cli._preprocess_argv()
        assert _sys.argv == ["mcmod-parser", "scan", "dir", "-o", "json"]

    def test_f_at_end_with_next_option(self) -> None:
        import sys as _sys
        from mcmod_parser import cli

        _sys.argv = ["mcmod-parser", "scan", "dir", "-f", "-r", "-o", "csv"]
        cli._preprocess_argv()
        # -f followed by -r (another option) → bare -f → -f .
        assert _sys.argv == ["mcmod-parser", "scan", "dir", "-f", ".", "-r", "-o", "csv"]
