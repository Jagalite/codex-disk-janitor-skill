#!/usr/bin/env python3
"""Read-only metadata scanner for Disk Space Janitor.

The scanner never deletes or modifies files. It requires explicit roots, uses
lstat, avoids following symlinks, records skipped mount-like boundaries, caps
traversal, and emits JSON for cleanup planning.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
import time
from collections import defaultdict
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


@dataclass
class Candidate:
    path: str
    type: str
    size_bytes: int
    modified_time: float | None
    access_time: float | None
    category: str


@dataclass
class DirectorySummary:
    path: str
    size_bytes: int
    item_count: int
    partial: bool


def categorize(path: Path, mode: int) -> str:
    name = path.name.lower()
    suffix = path.suffix.lower()
    parts = {part.lower() for part in path.parts}

    if stat.S_ISDIR(mode):
        if name in {"node_modules", "target", "dist", "build", ".next", ".turbo", "coverage", ".pytest_cache"}:
            return "build artifact"
        if name in {"cache", "caches", ".cache", "tmp", "temp"} or "cache" in name:
            return "cache"
        if name in {".git", ".hg", ".svn"}:
            return "source tree"
        if "docker" in parts:
            return "docker data"
        return "directory"

    if suffix in {".zip", ".tar", ".gz", ".tgz", ".7z", ".rar", ".xz", ".bz2"}:
        return "archive"
    if suffix in {".jpg", ".jpeg", ".png", ".gif", ".heic", ".mp4", ".mov", ".mkv", ".mp3", ".wav", ".flac"}:
        return "media"
    if suffix in {".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx", ".txt", ".md"}:
        return "document"
    if suffix in {".db", ".sqlite", ".sqlite3", ".mdb"}:
        return "database"
    if suffix in {".log", ".trace"}:
        return "log"
    if suffix in {".tmp", ".temp"}:
        return "temp file"
    if suffix in {".dmg", ".pkg", ".msi", ".exe", ".deb", ".rpm", ".appimage"}:
        return "installer"
    if suffix in {".py", ".js", ".ts", ".rs", ".go", ".java", ".c", ".cpp", ".cs", ".rb", ".php", ".sh"}:
        return "source file"
    return "file"


def human_size(value: int) -> str:
    units = ["B", "KiB", "MiB", "GiB", "TiB"]
    size = float(value)
    for unit in units:
        if size < 1024 or unit == units[-1]:
            return f"{size:.1f} {unit}" if unit != "B" else f"{int(size)} B"
        size /= 1024
    return f"{value} B"


def add_largest(items: list[Any], item: Any, limit: int, key: str = "size_bytes") -> None:
    items.append(item)
    items.sort(key=lambda entry: getattr(entry, key), reverse=True)
    del items[limit:]


def scan_root(root: Path, args: argparse.Namespace) -> dict[str, Any]:
    started_at = time.time()
    root = root.expanduser().resolve()
    partial_reasons: list[str] = []
    warnings: list[str] = []
    skipped_links: list[str] = []
    skipped_mounts: list[str] = []
    skipped_hidden: list[str] = []
    access_errors: list[str] = []
    largest_files: list[Candidate] = []
    largest_directories: list[DirectorySummary] = []
    extension_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "size_bytes": 0})
    category_counts: dict[str, dict[str, int]] = defaultdict(lambda: {"count": 0, "size_bytes": 0})
    directory_sizes: dict[str, int] = defaultdict(int)
    directory_counts: dict[str, int] = defaultdict(int)
    scanned_files = 0
    scanned_directories = 0
    root_device: int | None = None

    def note_partial(reason: str) -> None:
        if reason not in partial_reasons:
            partial_reasons.append(reason)

    try:
        root_stat = root.lstat()
        root_device = root_stat.st_dev
    except OSError as error:
        return {
            "root": str(root),
            "partial": True,
            "partial_reasons": [f"Could not stat root: {error}"],
            "warnings": [f"Could not stat root: {root}"],
        }

    if not root.exists():
        return {
            "root": str(root),
            "partial": True,
            "partial_reasons": ["Root does not exist"],
            "warnings": [f"Root does not exist: {root}"],
        }

    def visit(path: Path, depth: int) -> None:
        nonlocal scanned_files, scanned_directories
        if scanned_files >= args.max_files:
            note_partial(f"Stopped after max file limit: {args.max_files}")
            return
        if scanned_directories >= args.max_dirs:
            note_partial(f"Stopped after max directory limit: {args.max_dirs}")
            return
        try:
            info = path.lstat()
        except OSError as error:
            access_errors.append(str(path))
            note_partial(f"Access error: {path} ({error})")
            return

        mode = info.st_mode
        if path != root and not args.include_hidden and path.name.startswith("."):
            skipped_hidden.append(str(path))
            return

        if stat.S_ISLNK(mode):
            skipped_links.append(str(path))
            return

        if path != root and root_device is not None and info.st_dev != root_device:
            skipped_mounts.append(str(path))
            note_partial(f"Skipped mounted path or device boundary: {path}")
            return

        category = categorize(path, mode)
        category_counts[category]["count"] += 1
        category_counts[category]["size_bytes"] += info.st_size

        if stat.S_ISDIR(mode):
            scanned_directories += 1
            if depth >= args.max_depth:
                note_partial(f"Reached max depth at: {path}")
                return
            try:
                children = list(path.iterdir())
            except OSError as error:
                access_errors.append(str(path))
                note_partial(f"Could not list directory: {path} ({error})")
                return
            before_size = directory_sizes[str(path)]
            before_count = directory_counts[str(path)]
            for child in children:
                visit(child, depth + 1)
                if partial_reasons and (scanned_files >= args.max_files or scanned_directories >= args.max_dirs):
                    break
            summary = DirectorySummary(
                path=str(path),
                size_bytes=directory_sizes[str(path)] - before_size,
                item_count=directory_counts[str(path)] - before_count,
                partial=bool(partial_reasons),
            )
            add_largest(largest_directories, summary, args.top, key="size_bytes")
            return

        if stat.S_ISREG(mode):
            scanned_files += 1
            candidate = Candidate(
                path=str(path),
                type="file",
                size_bytes=info.st_size,
                modified_time=info.st_mtime,
                access_time=info.st_atime,
                category=category,
            )
            add_largest(largest_files, candidate, args.top)
            extension = path.suffix.lower() or "[no extension]"
            extension_counts[extension]["count"] += 1
            extension_counts[extension]["size_bytes"] += info.st_size
            for ancestor in path.parents:
                try:
                    ancestor.relative_to(root)
                except ValueError:
                    break
                directory_sizes[str(ancestor)] += info.st_size
                directory_counts[str(ancestor)] += 1
            return

        warnings.append(f"Skipped special file: {path}")

    visit(root, 0)

    return {
        "root": str(root),
        "partial": bool(partial_reasons),
        "partial_reasons": partial_reasons,
        "warnings": warnings,
        "elapsed_seconds": round(time.time() - started_at, 3),
        "scanned_files": scanned_files,
        "scanned_directories": scanned_directories,
        "skipped_links": skipped_links[: args.top],
        "skipped_mounts": skipped_mounts[: args.top],
        "skipped_hidden": skipped_hidden[: args.top],
        "access_errors": access_errors[: args.top],
        "largest_files": [asdict(item) | {"size": human_size(item.size_bytes)} for item in largest_files],
        "largest_directories": [asdict(item) | {"size": human_size(item.size_bytes)} for item in largest_directories],
        "extension_counts": dict(sorted(extension_counts.items())),
        "category_counts": dict(sorted(category_counts.items())),
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Read-only metadata scanner for Disk Space Janitor.")
    parser.add_argument("--root", action="append", required=True, help="Exact approved root to scan. Repeat for multiple roots.")
    parser.add_argument("--max-files", type=int, default=200_000, help="Stop after this many files.")
    parser.add_argument("--max-dirs", type=int, default=50_000, help="Stop after this many directories.")
    parser.add_argument("--max-depth", type=int, default=8, help="Maximum directory depth to traverse.")
    parser.add_argument("--top", type=int, default=30, help="Number of largest entries to keep.")
    parser.add_argument("--include-hidden", action="store_true", help="Include dotfiles and dotdirectories.")
    parser.add_argument("--json", action="store_true", help="Emit JSON. Present for explicitness; JSON is always emitted.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.max_files < 1 or args.max_dirs < 1 or args.max_depth < 0:
        print("Limits must be positive and max-depth must be non-negative.", file=sys.stderr)
        return 2
    reports = [scan_root(Path(root), args) for root in args.root]
    print(json.dumps({"reports": reports}, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
