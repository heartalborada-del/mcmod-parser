"""CLI entry point for mcmod-parser."""

from __future__ import annotations

import csv
import io
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import click

from mcmod_parser.jar_reader import parse_jar
from mcmod_parser.models import LoaderType
from mcmod_parser.scanner import parse_metadata_file, scan_directory


# ---------------------------------------------------------------------------
# Pre-process argv to support -f with an optional value:
#   -f alone       →  -f .   (auto-name in current directory)
#   -f some/path   →  -f some/path  (unchanged)
# ---------------------------------------------------------------------------
def _preprocess_argv() -> None:
    """Convert bare ``-f`` / ``--output-file`` to ``-f .`` so Click
    sees a value while the user can still omit it."""
    new_argv = [sys.argv[0]]
    args = sys.argv[1:]
    i = 0
    while i < len(args):
        a = args[i]
        if a in ("-f", "--output-file"):
            new_argv.append(a)
            # Peek at the next token – if it exists and is NOT an option
            # flag, treat it as the path value.
            if i + 1 < len(args) and not args[i + 1].startswith("-"):
                i += 1
                new_argv.append(args[i])
            else:
                new_argv.append(".")  # sentinel: auto-name in cwd
        else:
            new_argv.append(a)
        i += 1
    sys.argv = new_argv


_preprocess_argv()

# ---------------------------------------------------------------------------
OUTPUT_FORMATS = ["json", "table", "text", "csv"]
LOADER_CHOICES = [lt.value for lt in LoaderType]

_EXT_MAP = {"json": ".json", "csv": ".csv", "table": ".txt", "text": ".txt"}


def _format_table(mods: list) -> str:
    """Format mod list as a plain-text table."""
    if not mods:
        return "No mods found."

    # Determine column widths
    headers = ["Loader", "Mod ID", "Version", "Name"]
    rows: list[list[str]] = []
    for m in mods:
        name = m.display_name[:40] + "…" if len(m.display_name) > 40 else m.display_name
        rows.append([m.loader_type.value, m.mod_id, m.version, name])

    col_widths = [
        max(len(h), max((len(r[i]) for r in rows), default=0))
        for i, h in enumerate(headers)
    ]

    def fmt_row(cols: list[str]) -> str:
        return "│ " + " │ ".join(c.ljust(w) for c, w in zip(cols, col_widths)) + " │"

    sep = "├─" + "─┼─".join("─" * w for w in col_widths) + "─┤"
    top = "┌─" + "─┬─".join("─" * w for w in col_widths) + "─┐"
    bottom = "└─" + "─┴─".join("─" * w for w in col_widths) + "─┘"

    lines = [top, fmt_row(headers), sep]
    lines.extend(fmt_row(r) for r in rows)
    lines.append(bottom)
    return "\n".join(lines)


def _format_text(mods: list) -> str:
    """Format mod list as simple text lines."""
    if not mods:
        return "No mods found."
    lines = []
    for m in mods:
        lines.append(f"[{m.loader_type.value}] {m.mod_id}@{m.version} — {m.display_name}")
    return "\n".join(lines)


def _format_csv(mods: list) -> str:
    """Format mod list as CSV."""
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Loader", "ModID", "Version", "DisplayName", "Authors", "License", "Dependencies"])
    for m in mods:
        deps = "; ".join(f"{d.mod_id}:{d.version_range}" for d in m.dependencies)
        writer.writerow([
            m.loader_type.value,
            m.mod_id,
            m.version,
            m.display_name,
            str(m.authors),
            m.license,
            deps,
        ])
    return output.getvalue().rstrip("\r\n")


def _resolve_output_path(
    output_file: str | None,
    fmt: str,
    *,
    source: Path | None = None,
) -> Path | None:
    """Resolve the actual output file path.

    - ``None`` → stdout (returns ``None``).
    - ``"."`` → auto-generate a filename in the current directory.
    - A directory (existing, or a bare name without extension) →
      auto-generate a filename inside that directory.
    - A file path → used as-is.

    Auto-generated names are derived from *source* (e.g. the scanned
    directory or parsed JAR) and the chosen format.
    """
    if output_file is None:
        return None

    path = Path(output_file)
    # Treat as directory: ".", existing directory, or a name without extension
    is_dir = path.name == "." or path.is_dir() or path.suffix == ""
    if is_dir:
        stem = source.stem if source else "mcmod_output"
        ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        name = f"{stem}_{ts}{_EXT_MAP.get(fmt, '.txt')}"
        # Use the specified directory if it exists or has no extension;
        # otherwise fall back to cwd.
        base = path if (path.is_dir() or path.suffix == "") else Path(".")
        return base / name

    return path


def _build_content(mods: list, fmt: str) -> str:
    """Serialize *mods* to a string in the given format."""
    if fmt == "json":
        return json.dumps(
            [m.to_json_dict() for m in mods],
            indent=2,
            ensure_ascii=False,
        )
    elif fmt == "csv":
        return _format_csv(mods)
    elif fmt == "table":
        return _format_table(mods)
    else:
        return _format_text(mods)


def _output(
    mods: list,
    fmt: str,
    output_file: str | None = None,
    *,
    source: Path | None = None,
) -> None:
    """Output mod info in the requested format.

    Args:
        mods: Parsed ModInfo list.
        fmt: One of json, table, text, csv.
        output_file: Destination path, ``"."`` for auto-name, or ``None`` for stdout.
        source: Source path used to derive an auto-generated filename.
    """
    resolved = _resolve_output_path(output_file, fmt, source=source)
    content = _build_content(mods, fmt)

    if resolved:
        resolved.write_text(content, encoding="utf-8")
        click.echo(f"Saved to {resolved}")
    else:
        click.echo(content)


@click.group()
@click.version_option(package_name="mcmod-parser")
def main() -> None:
    """Parse Minecraft mod metadata from Forge/NeoForge/Fabric/Quilt JARs."""
    pass


@main.command()
@click.argument("path", type=click.Path(exists=True))
@click.option(
    "--output", "-o",
    type=click.Choice(OUTPUT_FORMATS),
    default="json",
    help="Output format (default: json).",
)
@click.option(
    "--output-file", "-f",
    type=click.Path(writable=True),
    default=None,
    help="Export to a file. Use '-f' alone to auto-name in current directory, "
         "or '-f path' for a specific destination.",
)
@click.option(
    "--loader", "-l",
    type=click.Choice(LOADER_CHOICES),
    default=None,
    help="Force a specific loader type.",
)
def parse(path: str, output: str, output_file: str | None, loader: str | None) -> None:
    """Parse a single JAR file or metadata file.

    PATH can be a .jar, mods.toml, fabric.mod.json, or quilt.mod.json.
    """
    p = Path(path)
    suffix = p.suffix.lower()

    try:
        if suffix == ".jar":
            mods = parse_jar(p)
        else:
            mods = parse_metadata_file(p)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    if loader:
        filter_type = LoaderType(loader)
        mods = [m for m in mods if m.loader_type == filter_type]

    _output(mods, output, output_file, source=p)


@main.command()
@click.argument("directory", type=click.Path(exists=True, file_okay=False))
@click.option(
    "--output", "-o",
    type=click.Choice(OUTPUT_FORMATS),
    default="json",
    help="Output format (default: json).",
)
@click.option(
    "--output-file", "-f",
    type=click.Path(writable=True),
    default=None,
    help="Export to a file. Use '-f' alone to auto-name in current directory, "
         "or '-f path' for a specific destination.",
)
@click.option(
    "--recursive", "-r",
    is_flag=True,
    default=False,
    help="Scan subdirectories recursively.",
)
@click.option(
    "--loader", "-l",
    type=click.Choice(LOADER_CHOICES),
    default=None,
    help="Only show mods of a specific loader type.",
)
def scan(directory: str, output: str, output_file: str | None, recursive: bool, loader: str | None) -> None:
    """Scan a directory for mod JARs and metadata files.

    DIRECTORY is the path to a mods folder.
    """
    filter_type = LoaderType(loader) if loader else None

    try:
        mods = scan_directory(directory, recursive=recursive, filter_loader=filter_type)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)

    _output(mods, output, output_file, source=Path(directory))


if __name__ == "__main__":
    main()
