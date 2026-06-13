"""Tests for CLI commands."""

import io
import json
import zipfile
from pathlib import Path

from click.testing import CliRunner

from mcmod_parser.cli import main, _format_diff, _render_diff
from mcmod_parser.models import LoaderType, ModInfo


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


# ---------------------------------------------------------------------------
# Diff tests
# ---------------------------------------------------------------------------

def _make_mod(mod_id: str, version: str, display_name: str = "", loader: LoaderType = LoaderType.FABRIC) -> ModInfo:
    return ModInfo(mod_id=mod_id, version=version, display_name=display_name, loader_type=loader)


class TestFormatDiff:
    def test_added(self) -> None:
        old = {"a": _make_mod("a", "1.0")}
        new = {"a": _make_mod("a", "1.0"), "b": _make_mod("b", "2.0")}
        items = _format_diff(old, new, "/old", "/new")
        added = [t for t, c in items if c == "green" and t.startswith("+")]
        assert any("b" in t for t in added)

    def test_removed(self) -> None:
        old = {"a": _make_mod("a", "1.0"), "b": _make_mod("b", "2.0")}
        new = {"a": _make_mod("a", "1.0")}
        items = _format_diff(old, new, "/old", "/new")
        removed = [t for t, c in items if c == "red" and t.startswith("-")]
        assert any("b" in t for t in removed)

    def test_version_changed(self) -> None:
        old = {"a": _make_mod("a", "1.0")}
        new = {"a": _make_mod("a", "2.0")}
        items = _format_diff(old, new, "/old", "/new")
        lines_red = [t for t, c in items if c == "red" and "a" in t]
        lines_green = [t for t, c in items if c == "green" and "a" in t]
        assert len(lines_red) == 1 and "1.0" in lines_red[0]
        assert len(lines_green) == 1 and "2.0" in lines_green[0]

    def test_unchanged_not_shown(self) -> None:
        old = {"a": _make_mod("a", "1.0")}
        new = {"a": _make_mod("a", "1.0")}
        items = _format_diff(old, new, "/old", "/new")
        body = [t for t, c in items if c in ("green", "red")]
        assert body == []  # no diff lines for unchanged

    def test_empty_both(self) -> None:
        items = _format_diff({}, {}, "/old", "/new")
        assert items == [("Both directories contain no mods.", None)]

    def test_header_labels(self) -> None:
        items = _format_diff(
            {"a": _make_mod("a", "1.0")}, {"a": _make_mod("a", "2.0")},
            "/mods/v1", "/mods/v2",
        )
        texts = [t for t, _ in items]
        assert any("--- /mods/v1" in t for t in texts)
        assert any("+++ /mods/v2" in t for t in texts)

    def test_summary_counts(self) -> None:
        old = {"a": _make_mod("a", "1.0"), "c": _make_mod("c", "1.0")}
        new = {"b": _make_mod("b", "2.0"), "c": _make_mod("c", "3.0")}
        items = _format_diff(old, new, "/old", "/new")
        summary = [t for t, c in items if "added" in t and c is None]
        assert len(summary) == 1
        assert "+1 added" in summary[0]
        assert "-1 removed" in summary[0]
        assert "~1 changed" in summary[0]


class TestRenderDiff:
    def test_colored(self) -> None:
        items = [("+ added", "green"), ("- removed", "red")]
        out = _render_diff(items, colored=True)
        assert "\033[" in out  # ANSI escape present

    def test_no_color(self) -> None:
        items = [("+ added", "green"), ("- removed", "red")]
        out = _render_diff(items, colored=False)
        assert "\033[" not in out
        assert "+ added" in out
        assert "- removed" in out


class TestCLIDiff:
    def test_diff_basic(self, tmp_path) -> None:
        runner = CliRunner()
        dir_a = tmp_path / "mods_a"
        dir_b = tmp_path / "mods_b"
        dir_a.mkdir()
        dir_b.mkdir()

        (dir_a / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "shared", "version": "1.0",
        }))
        (dir_a / "mod1.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "only_in_a", "version": "1.0",
        }))

        (dir_b / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "shared", "version": "2.0",
        }))
        (dir_b / "mod2.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "only_in_b", "version": "3.0",
        }))

        result = runner.invoke(main, ["diff", str(dir_a), str(dir_b)])
        assert result.exit_code == 0
        assert "only_in_a" in result.output
        assert "only_in_b" in result.output
        # shared version changed: 1.0 → 2.0
        assert "shared" in result.output

    def test_diff_no_color(self, tmp_path) -> None:
        runner = CliRunner()
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        (dir_a / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "m", "version": "1.0",
        }))
        (dir_b / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "m", "version": "2.0",
        }))

        result = runner.invoke(main, ["diff", str(dir_a), str(dir_b), "--no-color"])
        assert result.exit_code == 0
        assert "\033[" not in result.output  # no ANSI codes
        assert "m" in result.output
        assert "1.0" in result.output
        assert "2.0" in result.output

    def test_diff_output_file(self, tmp_path) -> None:
        runner = CliRunner()
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        (dir_a / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "m", "version": "1.0",
        }))
        (dir_b / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "m", "version": "1.0",
        }))

        out_f = tmp_path / "diff.txt"
        result = runner.invoke(main, [
            "diff", str(dir_a), str(dir_b),
            "--output-file", str(out_f),
        ])
        assert result.exit_code == 0
        assert out_f.is_file()
        content = out_f.read_text(encoding="utf-8")
        assert "m" in content

    def test_diff_empty_dirs(self, tmp_path) -> None:
        runner = CliRunner()
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        result = runner.invoke(main, ["diff", str(dir_a), str(dir_b)])
        assert result.exit_code == 0
        assert "no mods" in result.output.lower()

    def test_diff_loader_filter(self, tmp_path) -> None:
        runner = CliRunner()
        dir_a = tmp_path / "a"
        dir_b = tmp_path / "b"
        dir_a.mkdir()
        dir_b.mkdir()

        # Fabric mod
        (dir_a / "fabric.mod.json").write_text(json.dumps({
            "schemaVersion": 1, "id": "fabric_mod", "version": "1.0",
        }))
        # Forge mod
        (dir_a / "mods.toml").write_text("""\
license = "MIT"
[[mods]]
modId = "forge_mod"
version = "1.0"
""")
        (dir_b / "mods.toml").write_text("""\
license = "MIT"
[[mods]]
modId = "forge_mod"
version = "2.0"
""")

        # Only compare forge mods
        result = runner.invoke(main, [
            "diff", str(dir_a), str(dir_b), "--loader", "forge",
        ])
        assert result.exit_code == 0
        assert "forge_mod" in result.output
        assert "fabric_mod" not in result.output

    def test_diff_help(self) -> None:
        runner = CliRunner()
        result = runner.invoke(main, ["diff", "--help"])
        assert result.exit_code == 0
        assert "DIR_A" in result.output
        assert "--no-color" in result.output
        assert "--recursive" in result.output
