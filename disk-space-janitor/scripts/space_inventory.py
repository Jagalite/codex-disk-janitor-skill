#!/usr/bin/env python3
"""Read-only disk-space inventory helper.

The script reports large files, large directories, stale downloads, and known
cleanup-oriented locations. It never deletes or modifies files.
"""

from __future__ import annotations

import argparse
import json
import os
import platform
import sys
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable


DEFAULT_MAX_FILES = 200_000
DEFAULT_MIN_FILE_MB = 100
STALE_DAYS = 90


@dataclass
class FileEntry:
    path: str
    size: int
    modified: float


@dataclass
class DirEntry:
    path: str
    size: int
    file_count: int
    partial: bool = False


@dataclass
class KnownLocation:
    path: str
    category: str
    risk: str
    note: str
    size: int | None = None
    partial: bool = False


@dataclass
class TopLevelEntry:
    path: str
    size: int
    file_count: int
    dir_count: int
    partial: bool = False


def human_size(value: int | None) -> str:
    if value is None:
        return "unknown"
    units = ["B", "KiB", "MiB", "GiB", "TiB", "PiB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def safe_stat(path: Path):
    try:
        return path.stat()
    except OSError:
        return None


def make_walk_error_handler(note_partial):
    def onerror(error: OSError) -> None:
        filename = getattr(error, "filename", None) or "unknown path"
        note_partial(f"Could not fully scan: {filename} ({error.strerror or error})")

    return onerror


def is_hidden(path: Path, root: Path | None = None) -> bool:
    parts = path.parts
    if root is not None:
        try:
            parts = path.relative_to(root).parts
        except ValueError:
            parts = path.parts
    return any(part.startswith(".") for part in parts if part not in (path.anchor, os.sep, "."))


def iter_known_locations() -> list[KnownLocation]:
    home = Path.home()
    system = platform.system().lower()
    locations: list[KnownLocation] = []
    seen: set[str] = set()

    def add(path: Path | str | None, category: str, risk: str, note: str) -> None:
        if not path:
            return
        candidate = Path(path).expanduser()
        if not candidate.exists():
            return
        key = str(candidate.resolve()).lower() if system == "windows" else str(candidate.resolve())
        if key in seen:
            return
        seen.add(key)
        locations.append(KnownLocation(str(candidate), category, risk, note))

    add(home / "Downloads", "downloads", "medium", "Review old installers, archives, and large personal files.")
    add(home / ".cache", "cache", "low", "Usually regenerated; prefer app/package-manager cleanup when possible.")

    if system == "windows":
        add(os.environ.get("TEMP"), "temp", "low", "User temp directory; close apps before cleaning.")
        add(os.environ.get("LOCALAPPDATA") and Path(os.environ["LOCALAPPDATA"]) / "Temp", "temp", "low", "Local app temp directory.")
        add(os.environ.get("LOCALAPPDATA") and Path(os.environ["LOCALAPPDATA"]) / "CrashDumps", "logs", "low", "Crash dump files; useful only for debugging.")
    elif system == "darwin":
        add(home / "Library" / "Caches", "cache", "low", "User caches; prefer app cleanup for large app-specific folders.")
        add(home / "Library" / "Developer" / "Xcode" / "DerivedData", "development", "low", "Xcode build artifacts that can be regenerated.")
        add(home / "Library" / "Developer" / "CoreSimulator", "development", "medium", "Simulator data; use Xcode tools or UI when possible.")
    else:
        add(home / ".cache" / "pip", "development", "low", "Python package cache.")
        add(home / ".npm", "development", "low", "npm cache or metadata; use npm cache commands when possible.")
        add(home / ".cargo" / "registry", "development", "medium", "Rust registry cache; can be large but may save download time.")

    return locations


def ancestors_within(root: Path, path: Path, max_depth: int) -> Iterable[Path]:
    try:
        rel = path.relative_to(root)
    except ValueError:
        return []
    parts = rel.parts[:-1] if path.is_file() else rel.parts
    current = root
    yield current
    for depth, part in enumerate(parts, start=1):
        if depth > max_depth:
            break
        current = current / part
        yield current


def scan_roots(
    roots: list[Path],
    max_depth: int,
    top: int,
    min_file_size: int,
    include_hidden: bool,
    max_files: int,
    size_known_locations: bool,
    progress_seconds: float,
    summary_mode: str,
) -> dict:
    if summary_mode == "top-level":
        return scan_top_level(roots, top, include_hidden, max_files, progress_seconds, size_known_locations)

    large_files: list[FileEntry] = []
    stale_downloads: list[FileEntry] = []
    dir_sizes: dict[str, int] = {}
    dir_counts: dict[str, int] = {}
    errors: list[str] = []
    partial_reasons: list[str] = []
    extension_counts: dict[str, dict[str, int]] = {}
    scanned_files = 0
    scanned_dirs = 0
    skipped_reparse_points = 0
    now = time.time()
    stale_cutoff = now - (STALE_DAYS * 24 * 60 * 60)
    started_at = now
    next_progress_at = started_at + progress_seconds if progress_seconds > 0 else None

    def note_partial(reason: str) -> None:
        if reason not in partial_reasons:
            partial_reasons.append(reason)

    def record_extension(path: Path, size: int) -> None:
        extension = path.suffix.lower() or "[no extension]"
        entry = extension_counts.setdefault(extension, {"file_count": 0, "size_bytes": 0})
        entry["file_count"] += 1
        entry["size_bytes"] += size

    def maybe_progress(current_root: Path) -> None:
        nonlocal next_progress_at
        if next_progress_at is None:
            return
        now_progress = time.time()
        if now_progress < next_progress_at:
            return
        elapsed = now_progress - started_at
        largest = max((item.size for item in large_files), default=0)
        largest_dir = max(dir_sizes.values(), default=0)
        print(
            f"[progress] elapsed={elapsed:.1f}s root={current_root} "
            f"phase=inventory files={scanned_files} dirs={scanned_dirs} "
            f"large_candidates={len(large_files)} largest_file={human_size(largest)} "
            f"largest_dir={human_size(largest_dir)} partial={bool(partial_reasons)}",
            file=sys.stderr,
        )
        next_progress_at = now_progress + progress_seconds

    for raw_root in roots:
        root = raw_root.expanduser().resolve()
        if not root.exists():
            errors.append(f"Root does not exist: {root}")
            continue
        if root.is_file():
            stat = safe_stat(root)
            if stat and stat.st_size >= min_file_size:
                large_files.append(FileEntry(str(root), stat.st_size, stat.st_mtime))
            continue

        for current, dirs, files in os.walk(root, topdown=True, followlinks=False, onerror=make_walk_error_handler(note_partial)):
            scanned_dirs += 1
            current_path = Path(current)
            if not include_hidden:
                dirs[:] = [name for name in dirs if not name.startswith(".")]
                files = [name for name in files if not name.startswith(".")]
                if is_hidden(current_path, root) and current_path != root:
                    dirs[:] = []
                    continue

            kept_dirs = []
            for name in dirs:
                if (current_path / name).is_symlink():
                    skipped_reparse_points += 1
                else:
                    kept_dirs.append(name)
            dirs[:] = kept_dirs

            for name in files:
                if scanned_files >= max_files:
                    reason = f"Stopped after max file limit: {max_files}"
                    errors.append(reason)
                    note_partial(reason)
                    return finalize(
                        large_files,
                        stale_downloads,
                        dir_sizes,
                        dir_counts,
                        known_locations(size_known_locations, partial_reasons),
                        errors,
                        scanned_files,
                        scanned_dirs,
                        top,
                        partial_reasons,
                        started_at,
                        extension_counts,
                        skipped_reparse_points,
                    )

                path = current_path / name
                if path.is_symlink():
                    skipped_reparse_points += 1
                    continue
                stat = safe_stat(path)
                if not stat:
                    note_partial("Some files could not be statted or accessed.")
                    continue

                scanned_files += 1
                size = stat.st_size
                record_extension(path, size)
                for ancestor in ancestors_within(root, path, max_depth):
                    key = str(ancestor)
                    dir_sizes[key] = dir_sizes.get(key, 0) + size
                    dir_counts[key] = dir_counts.get(key, 0) + 1

                if size >= min_file_size:
                    large_files.append(FileEntry(str(path), size, stat.st_mtime))

                if "download" in str(path.parent).lower() and stat.st_mtime <= stale_cutoff:
                    stale_downloads.append(FileEntry(str(path), size, stat.st_mtime))
                maybe_progress(root)

    return finalize(
        large_files,
        stale_downloads,
        dir_sizes,
        dir_counts,
        known_locations(size_known_locations, partial_reasons),
        errors,
        scanned_files,
        scanned_dirs,
        top,
        partial_reasons,
        started_at,
        extension_counts,
        skipped_reparse_points,
    )


def dir_size_limited(path: Path, max_files: int = 50_000) -> tuple[int | None, bool]:
    total = 0
    count = 0
    partial = False
    try:
        def onerror(error: OSError) -> None:
            nonlocal partial
            partial = True

        for current, dirs, files in os.walk(path, topdown=True, followlinks=False, onerror=onerror):
            current_path = Path(current)
            dirs[:] = [name for name in dirs if not (current_path / name).is_symlink()]
            for name in files:
                if count >= max_files:
                    return total, True
                file_path = current_path / name
                if file_path.is_symlink():
                    continue
                stat = safe_stat(file_path)
                if stat:
                    total += stat.st_size
                    count += 1
                else:
                    partial = True
    except OSError:
        return None, True
    return total, partial


def known_locations(include_sizes: bool, partial_reasons: list[str] | None = None) -> list[KnownLocation]:
    locations = iter_known_locations()
    if not include_sizes:
        return locations
    for location in locations:
        path = Path(location.path)
        if path.is_file():
            stat = safe_stat(path)
            location.size = stat.st_size if stat else None
        elif path.is_dir():
            location.size, location.partial = dir_size_limited(path)
            if location.partial and partial_reasons is not None:
                partial_reasons.append(f"Known-location size capped or partially inaccessible: {path}")
    return locations


def scan_top_level(
    roots: list[Path],
    top: int,
    include_hidden: bool,
    max_files: int,
    progress_seconds: float,
    size_known_locations: bool,
) -> dict:
    entries: list[TopLevelEntry] = []
    warnings: list[str] = []
    partial_reasons: list[str] = []
    extension_counts: dict[str, dict[str, int]] = {}
    scanned_files = 0
    scanned_dirs = 0
    skipped_reparse_points = 0
    started_at = time.time()
    next_progress_at = started_at + progress_seconds if progress_seconds > 0 else None

    def note_partial(reason: str) -> None:
        if reason not in partial_reasons:
            partial_reasons.append(reason)

    def record_extension(path: Path, size: int) -> None:
        extension = path.suffix.lower() or "[no extension]"
        entry = extension_counts.setdefault(extension, {"file_count": 0, "size_bytes": 0})
        entry["file_count"] += 1
        entry["size_bytes"] += size

    def maybe_progress(root: Path) -> None:
        nonlocal next_progress_at
        if next_progress_at is None:
            return
        now_progress = time.time()
        if now_progress < next_progress_at:
            return
        elapsed = now_progress - started_at
        largest_dir = max((item.size for item in entries), default=0)
        print(
            f"[progress] elapsed={elapsed:.1f}s root={root} phase=top-level "
            f"files={scanned_files} dirs={scanned_dirs} top_items={len(entries)} "
            f"largest_dir={human_size(largest_dir)} partial={bool(partial_reasons)}",
            file=sys.stderr,
        )
        next_progress_at = now_progress + progress_seconds

    for raw_root in roots:
        root = raw_root.expanduser().resolve()
        if not root.exists():
            warnings.append(f"Root does not exist: {root}")
            note_partial(f"Root does not exist: {root}")
            continue
        if root.is_file():
            stat = safe_stat(root)
            if stat:
                entries.append(TopLevelEntry(str(root), stat.st_size, 1, 0))
                record_extension(root, stat.st_size)
                scanned_files += 1
            continue
        try:
            children = list(root.iterdir())
        except OSError as error:
            warnings.append(f"Could not list root {root}: {error}")
            note_partial(f"Could not list root: {root}")
            continue
        for child in children:
            if not include_hidden and child.name.startswith("."):
                continue
            maybe_progress(root)
            if child.is_symlink():
                skipped_reparse_points += 1
                note_partial(f"Skipped symlink or reparse point: {child}")
                continue
            if child.is_file():
                stat = safe_stat(child)
                if stat:
                    entries.append(TopLevelEntry(str(child), stat.st_size, 1, 0))
                    record_extension(child, stat.st_size)
                    scanned_files += 1
                else:
                    note_partial(f"Could not stat file: {child}")
                continue
            if child.is_dir():
                total = 0
                file_count = 0
                dir_count = 0
                partial = False
                try:
                    def on_child_error(error: OSError) -> None:
                        nonlocal partial
                        partial = True
                        note_partial(f"Could not fully scan: {getattr(error, 'filename', None) or child} ({error.strerror or error})")

                    for current, dirs, files in os.walk(child, topdown=True, followlinks=False, onerror=on_child_error):
                        scanned_dirs += 1
                        dir_count += 1
                        current_path = Path(current)
                        kept_dirs = []
                        for name in dirs:
                            if (current_path / name).is_symlink():
                                partial = True
                                skipped_reparse_points += 1
                            else:
                                kept_dirs.append(name)
                        dirs[:] = kept_dirs
                        for name in files:
                            if scanned_files >= max_files:
                                partial = True
                                reason = f"Stopped top-level summary after max file limit: {max_files}"
                                note_partial(reason)
                                warnings.append(reason)
                                entries.append(TopLevelEntry(str(child), total, file_count, dir_count, partial))
                                return finalize_top_level(entries, warnings, partial_reasons, scanned_files, scanned_dirs, top, started_at, size_known_locations, extension_counts, skipped_reparse_points)
                            file_path = current_path / name
                            if file_path.is_symlink():
                                partial = True
                                skipped_reparse_points += 1
                                continue
                            stat = safe_stat(file_path)
                            if stat:
                                total += stat.st_size
                                file_count += 1
                                scanned_files += 1
                                record_extension(file_path, stat.st_size)
                                maybe_progress(root)
                            else:
                                partial = True
                                note_partial("Some files could not be statted or accessed.")
                except OSError as error:
                    warnings.append(f"Could not fully scan {child}: {error}")
                    note_partial(f"Could not fully scan: {child}")
                    partial = True
                entries.append(TopLevelEntry(str(child), total, file_count, dir_count, partial))
    return finalize_top_level(entries, warnings, partial_reasons, scanned_files, scanned_dirs, top, started_at, size_known_locations, extension_counts, skipped_reparse_points)


def finalize_top_level(
    entries: list[TopLevelEntry],
    warnings: list[str],
    partial_reasons: list[str],
    scanned_files: int,
    scanned_dirs: int,
    top: int,
    started_at: float,
    size_known_locations: bool,
    extension_counts: dict[str, dict[str, int]],
    skipped_reparse_points: int,
) -> dict:
    top_entries = sorted(entries, key=lambda item: item.size, reverse=True)[:top]
    locations = [asdict(item) for item in known_locations(size_known_locations, partial_reasons)]
    return {
        "mode": "top-level",
        "size_units": "binary; human sizes use KiB/MiB/GiB and JSON size fields are bytes",
        "partial": bool(partial_reasons),
        "partial_reasons": sorted(set(partial_reasons)),
        "elapsed_seconds": round(time.time() - started_at, 3),
        "scanned_files": scanned_files,
        "scanned_directories": scanned_dirs,
        "skipped_reparse_points": skipped_reparse_points,
        "extension_counts": dict(sorted(extension_counts.items())),
        "top_level": [asdict(item) for item in top_entries],
        "large_files": [],
        "large_directories": [],
        "stale_downloads": [],
        "known_locations": locations,
        "warnings": warnings,
    }


def finalize(
    large_files: list[FileEntry],
    stale_downloads: list[FileEntry],
    dir_sizes: dict[str, int],
    dir_counts: dict[str, int],
    locations: list[KnownLocation],
    errors: list[str],
    scanned_files: int,
    scanned_dirs: int,
    top: int,
    partial_reasons: list[str],
    started_at: float,
    extension_counts: dict[str, dict[str, int]],
    skipped_reparse_points: int,
) -> dict:
    top_files = sorted(large_files, key=lambda item: item.size, reverse=True)[:top]
    top_stale = sorted(stale_downloads, key=lambda item: item.size, reverse=True)[:top]
    top_dirs = sorted(
        (DirEntry(path, size, dir_counts.get(path, 0)) for path, size in dir_sizes.items()),
        key=lambda item: item.size,
        reverse=True,
    )[:top]
    top_locations = sorted(locations, key=lambda item: item.size or 0, reverse=True)
    return {
        "mode": "inventory",
        "size_units": "binary; human sizes use KiB/MiB/GiB and JSON size fields are bytes",
        "partial": bool(partial_reasons),
        "partial_reasons": sorted(set(partial_reasons)),
        "elapsed_seconds": round(time.time() - started_at, 3),
        "scanned_files": scanned_files,
        "scanned_directories": scanned_dirs,
        "skipped_reparse_points": skipped_reparse_points,
        "extension_counts": dict(sorted(extension_counts.items())),
        "top_level": [],
        "large_files": [asdict(item) for item in top_files],
        "large_directories": [asdict(item) for item in top_dirs],
        "stale_downloads": [asdict(item) for item in top_stale],
        "known_locations": [asdict(item) for item in top_locations],
        "warnings": errors,
    }


def render_markdown(report: dict) -> str:
    lines = [
        "# Disk Space Inventory",
        "",
        f"Mode: {report.get('mode', 'inventory')}",
        f"Status: {'partial' if report.get('partial') else 'complete'}",
        f"Units: {report.get('size_units', 'JSON sizes are bytes')}",
        f"Elapsed: {report.get('elapsed_seconds', 0)} seconds",
        f"Scanned files: {report['scanned_files']}",
        f"Scanned directories: {report.get('scanned_directories', 0)}",
        f"Skipped symlinks/reparse points: {report.get('skipped_reparse_points', 0)}",
        "",
    ]
    if report.get("partial_reasons"):
        lines.extend(["## Partial Scan Reasons", ""])
        lines.extend(f"- {reason}" for reason in report["partial_reasons"])
        lines.append("")

    if report["warnings"]:
        lines.extend(["## Warnings", ""])
        lines.extend(f"- {warning}" for warning in report["warnings"])
        lines.append("")

    def table(title: str, rows: list[dict], columns: list[tuple[str, str]]) -> None:
        lines.extend([f"## {title}", ""])
        if not rows:
            lines.extend(["No entries found.", ""])
            return
        lines.append("| " + " | ".join(label for label, _ in columns) + " |")
        lines.append("| " + " | ".join("---" for _ in columns) + " |")
        for row in rows:
            values = []
            for _, key in columns:
                value = row.get(key, "")
                if key == "size":
                    value = human_size(value)
                values.append(str(value).replace("|", "\\|"))
            lines.append("| " + " | ".join(values) + " |")
        lines.append("")

    table("Largest Directories", report["large_directories"], [("Size", "size"), ("Files", "file_count"), ("Path", "path")])
    table("Top-Level Summary", report.get("top_level", []), [("Size", "size"), ("Files", "file_count"), ("Dirs", "dir_count"), ("Partial", "partial"), ("Path", "path")])
    table("Largest Files", report["large_files"], [("Size", "size"), ("Path", "path")])
    table("Stale Downloads", report["stale_downloads"], [("Size", "size"), ("Path", "path")])
    extension_rows = [
        {"extension": extension, **data}
        for extension, data in sorted(
            report.get("extension_counts", {}).items(),
            key=lambda item: item[1].get("size_bytes", 0),
            reverse=True,
        )
    ]
    table("Extension Summary", extension_rows, [("Size", "size_bytes"), ("Files", "file_count"), ("Extension", "extension")])
    table("Known Cleanup Locations", report["known_locations"], [("Size", "size"), ("Partial", "partial"), ("Risk", "risk"), ("Category", "category"), ("Path", "path"), ("Note", "note")])
    return "\n".join(lines)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only disk-space inventory helper.")
    parser.add_argument("--root", action="append", default=[], help="Root folder to scan. Repeat for multiple approved roots.")
    parser.add_argument("--max-depth", type=int, default=4, help="Maximum directory depth to aggregate from each root.")
    parser.add_argument("--top", type=int, default=30, help="Number of entries to show per section.")
    parser.add_argument("--min-file-size-mb", type=int, default=DEFAULT_MIN_FILE_MB, help="Minimum file size for largest-file reporting.")
    parser.add_argument("--max-files", type=int, default=DEFAULT_MAX_FILES, help="Stop scanning after this many files.")
    parser.add_argument("--include-hidden", action="store_true", help="Include hidden dotfiles and dotfolders.")
    parser.add_argument("--size-known-locations", action="store_true", help="Estimate sizes for known cleanup locations. This can be slow on large home folders.")
    parser.add_argument("--progress-seconds", type=float, default=0, help="Print progress updates to stderr at this interval. Use 5 for long interactive scans.")
    parser.add_argument("--summary-mode", choices=("inventory", "top-level"), default="inventory", help="Use top-level for a fast immediate-child folder size summary.")
    parser.add_argument("--format", choices=("markdown", "json"), default="markdown", help="Output format.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if not args.root:
        print("At least one explicit --root is required.", file=sys.stderr)
        return 2
    roots = [Path(item) for item in args.root]
    report = scan_roots(
        roots=roots,
        max_depth=max(0, args.max_depth),
        top=max(1, args.top),
        min_file_size=max(0, args.min_file_size_mb) * 1024 * 1024,
        include_hidden=args.include_hidden,
        max_files=max(1, args.max_files),
        size_known_locations=args.size_known_locations,
        progress_seconds=max(0.0, args.progress_seconds),
        summary_mode=args.summary_mode,
    )
    if args.format == "json":
        print(json.dumps(report, indent=2))
    else:
        print(render_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
