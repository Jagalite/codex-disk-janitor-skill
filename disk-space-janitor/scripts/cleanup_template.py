#!/usr/bin/env python3
"""Reviewable cleanup runner template for Disk Space Janitor.

Copy this file to CodexJanitor/<run-id>/cleanup.py and pair it with a
cleanup_manifest.json generated from the final approved cleanup draft.

The script is intentionally plain: exact approved paths are loaded from the
manifest, dry-run is the default, and every write mode performs measure-twice
checks before touching files.
"""

from __future__ import annotations

import argparse
import ctypes
import json
import os
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any


SELF_TEST_DIR = "self-test"
DEFAULT_LOG_NAME = "cleanup-log.jsonl"


@dataclass
class CleanupItem:
    item_id: str
    original_path: Path
    action: str
    size_bytes: int
    description: str
    risk: str
    allowed_extensions: list[str]
    staged_relative_path: str | None = None


def load_manifest(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Manifest must be a JSON object.")
    if not isinstance(data.get("items"), list):
        raise ValueError("Manifest must include an items list.")
    return data


def item_from_manifest(raw: dict[str, Any]) -> CleanupItem:
    return CleanupItem(
        item_id=str(raw["id"]),
        original_path=Path(raw["original_path"]).expanduser().resolve(),
        action=str(raw.get("action", "stage")),
        size_bytes=int(raw.get("size_bytes", 0)),
        description=str(raw.get("description", "")),
        risk=str(raw.get("risk", "unknown")),
        allowed_extensions=[str(item).lower() for item in raw.get("allowed_extensions", [])],
        staged_relative_path=raw.get("staged_relative_path"),
    )


def is_dangerous_root(path: Path) -> bool:
    resolved = path.resolve()
    anchors = {Path(resolved.anchor).resolve()} if resolved.anchor else set()
    home = Path.home().resolve()
    dangerous = anchors | {home}
    try:
        cwd = Path.cwd().resolve()
        dangerous.add(cwd)
    except OSError:
        pass
    return resolved in dangerous


def path_under(path: Path, prefixes: list[Path]) -> bool:
    resolved = path.resolve()
    for prefix in prefixes:
        try:
            resolved.relative_to(prefix.resolve())
            return True
        except ValueError:
            continue
    return False


def directory_size(path: Path) -> int:
    if path.is_file():
        return path.stat().st_size
    total = 0
    for current, dirs, files in os.walk(path, topdown=True, followlinks=False):
        current_path = Path(current)
        dirs[:] = [name for name in dirs if not (current_path / name).is_symlink()]
        for name in files:
            file_path = current_path / name
            if file_path.is_symlink():
                continue
            try:
                total += file_path.stat().st_size
            except OSError:
                pass
    return total


def append_log(log_path: Path, event: dict[str, Any]) -> None:
    event = {"time": time.strftime("%Y-%m-%dT%H:%M:%S%z"), **event}
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(event, ensure_ascii=False) + "\n")


def recycle_windows(path: Path) -> None:
    # SHFileOperationW with FOF_ALLOWUNDO moves to Recycle Bin.
    # The double-NUL path terminator is required by the Win32 API.
    shell32 = ctypes.windll.shell32
    from ctypes import wintypes

    FO_DELETE = 0x0003
    FOF_ALLOWUNDO = 0x0040
    FOF_NOCONFIRMATION = 0x0010
    FOF_SILENT = 0x0004
    FOF_NOERRORUI = 0x0400

    class SHFILEOPSTRUCTW(ctypes.Structure):
        _fields_ = [
            ("hwnd", wintypes.HWND),
            ("wFunc", wintypes.UINT),
            ("pFrom", wintypes.LPCWSTR),
            ("pTo", wintypes.LPCWSTR),
            ("fFlags", wintypes.WORD),
            ("fAnyOperationsAborted", wintypes.BOOL),
            ("hNameMappings", wintypes.LPVOID),
            ("lpszProgressTitle", wintypes.LPCWSTR),
        ]

    operation = SHFILEOPSTRUCTW()
    operation.wFunc = FO_DELETE
    operation.pFrom = str(path) + "\0\0"
    operation.fFlags = FOF_ALLOWUNDO | FOF_NOCONFIRMATION | FOF_SILENT | FOF_NOERRORUI
    result = shell32.SHFileOperationW(ctypes.byref(operation))
    if result != 0 or operation.fAnyOperationsAborted:
        raise OSError(f"Recycle Bin operation failed for {path}; code={result}")


def move_to_trash(path: Path) -> None:
    if sys.platform == "win32":
        recycle_windows(path)
        return
    trash_dir = Path.home() / ".Trash"
    trash_dir.mkdir(exist_ok=True)
    shutil.move(str(path), str(trash_dir / path.name))


def stage_item(item: CleanupItem, run_dir: Path) -> Path:
    items_root = (run_dir / "items").resolve()
    if item.staged_relative_path:
        relative = Path(item.staged_relative_path)
        if relative.is_absolute() or ".." in relative.parts:
            raise ValueError(f"Unsafe staged_relative_path for {item.item_id}: {item.staged_relative_path}")
        if relative.parts and relative.parts[0].lower() == "items":
            destination = (run_dir / relative).resolve()
        else:
            destination = (items_root / relative).resolve()
    else:
        safe_name = f"{item.item_id}-{item.original_path.name}"
        destination = (items_root / safe_name).resolve()
    try:
        destination.relative_to(items_root)
    except ValueError as error:
        raise ValueError(f"Staging destination escapes items folder for {item.item_id}: {destination}") from error
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(item.original_path), str(destination))
    return destination


def delete_item(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
    else:
        path.unlink()


def preflight(items: list[CleanupItem], manifest: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    approved_prefixes = [Path(item).expanduser().resolve() for item in manifest.get("approved_prefixes", [])]
    expected_count = manifest.get("expected_count")
    expected_total = manifest.get("expected_total_size_bytes")

    if expected_count is not None and int(expected_count) != len(items):
        errors.append(f"Item count mismatch: manifest={expected_count} loaded={len(items)}")

    measured_total = 0
    for item in items:
        path = item.original_path
        if not path.exists():
            errors.append(f"Missing approved target: {item.item_id} {path}")
            continue
        if path.is_symlink():
            errors.append(f"Refusing symlink/reparse target: {item.item_id} {path}")
            continue
        if is_dangerous_root(path):
            errors.append(f"Refusing dangerous broad root: {item.item_id} {path}")
            continue
        if approved_prefixes and not path_under(path, approved_prefixes):
            errors.append(f"Path outside approved prefixes: {item.item_id} {path}")
            continue
        if item.allowed_extensions and path.is_file():
            extension = path.suffix.lower() or "[no extension]"
            if extension not in item.allowed_extensions:
                errors.append(f"Unexpected extension for {item.item_id}: {extension} {path}")
                continue
        try:
            measured_total += directory_size(path)
        except OSError as error:
            errors.append(f"Could not measure {item.item_id} {path}: {error}")

    if expected_total is not None:
        expected_total = int(expected_total)
        tolerance = max(1024 * 1024, int(expected_total * 0.05))
        if abs(measured_total - expected_total) > tolerance:
            errors.append(
                f"Measured size differs from manifest: expected={expected_total} actual={measured_total}"
            )

    return errors


def run_items(items: list[CleanupItem], run_dir: Path, mode: str, dry_run: bool, log_path: Path) -> int:
    failures = 0
    for item in items:
        target = item.original_path
        event: dict[str, Any] = {
            "item_id": item.item_id,
            "action": mode,
            "original_path": str(target),
            "size_bytes": item.size_bytes,
            "description": item.description,
            "risk": item.risk,
            "dry_run": dry_run,
        }
        if dry_run:
            event["outcome"] = "would-run"
            append_log(log_path, event)
            print(f"DRY-RUN {mode}: {item.item_id} {target}")
            continue
        try:
            if mode == "stage":
                staged_path = stage_item(item, run_dir)
                event["staged_path"] = str(staged_path)
            elif mode == "trash":
                move_to_trash(target)
            elif mode == "delete":
                delete_item(target)
            else:
                raise ValueError(f"Unsupported write mode: {mode}")
            event["outcome"] = "ok"
        except Exception as error:
            event["outcome"] = "failed"
            event["error"] = str(error)
            failures += 1
        append_log(log_path, event)
        print(f"{event['outcome'].upper()} {mode}: {item.item_id} {target}")
    return failures


def create_self_test_manifest(run_dir: Path) -> tuple[dict[str, Any], list[CleanupItem]]:
    test_root = run_dir / SELF_TEST_DIR
    source = test_root / "source"
    nested = source / "nested"
    nested.mkdir(parents=True, exist_ok=True)
    (source / "alpha.tmp").write_text("alpha", encoding="utf-8")
    (nested / "beta.log").write_text("beta" * 100, encoding="utf-8")
    items = [
        CleanupItem("test-1", source / "alpha.tmp", "stage", 5, "Self-test file", "low", [".tmp"]),
        CleanupItem("test-2", nested, "stage", directory_size(nested), "Self-test recursive folder", "low", []),
    ]
    manifest = {
        "run_id": "self-test",
        "approved_prefixes": [str(source.resolve())],
        "expected_count": len(items),
        "expected_total_size_bytes": sum(directory_size(item.original_path) for item in items),
        "items": [],
    }
    return manifest, items


def run_self_test(run_dir: Path) -> int:
    test_root = run_dir / SELF_TEST_DIR
    if test_root.exists():
        shutil.rmtree(test_root)
    manifest, items = create_self_test_manifest(run_dir)
    errors = preflight(items, manifest)
    if errors:
        for error in errors:
            print(f"SELF-TEST PREFLIGHT FAILED: {error}", file=sys.stderr)
        return 1
    log_path = test_root / "self-test-log.jsonl"
    if run_items(items, test_root, "stage", dry_run=True, log_path=log_path):
        return 1
    if run_items(items, test_root, "stage", dry_run=False, log_path=log_path):
        return 1
    expected = [test_root / "items" / f"{item.item_id}-{item.original_path.name}" for item in items]
    missing = [path for path in expected if not path.exists()]
    if missing:
        for path in missing:
            print(f"SELF-TEST FAILED missing staged item: {path}", file=sys.stderr)
        return 1
    print(f"SELF-TEST OK: {test_root}")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Reviewable cleanup runner template.")
    parser.add_argument("--manifest", default="cleanup_manifest.json", help="Machine-readable manifest JSON.")
    parser.add_argument("--run-dir", default=".", help="CodexJanitor run directory.")
    parser.add_argument("--log", default=DEFAULT_LOG_NAME, help="JSONL log path relative to run dir unless absolute.")
    parser.add_argument("--self-test", action="store_true", help="Run fake-file self-test under the run folder.")
    parser.add_argument("--dry-run", action="store_true", help="Preview actions without modifying targets.")
    parser.add_argument("--execute", action="store_true", help="Actually perform the selected write mode. Without this, write modes dry-run.")
    parser.add_argument("--stage", action="store_true", help="Move approved targets into run-dir/items.")
    parser.add_argument("--trash", action="store_true", help="Move approved targets to Trash/Recycle Bin.")
    parser.add_argument("--delete", action="store_true", help="Permanently delete approved targets.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).expanduser().resolve()
    run_dir.mkdir(parents=True, exist_ok=True)

    if args.self_test:
        return run_self_test(run_dir)

    modes = [name for name in ("stage", "trash", "delete") if getattr(args, name)]
    if len(modes) != 1:
        print("Choose exactly one write mode: --stage, --trash, or --delete.", file=sys.stderr)
        return 2
    mode = modes[0]

    manifest_path = Path(args.manifest).expanduser()
    if not manifest_path.is_absolute():
        manifest_path = run_dir / manifest_path
    manifest = load_manifest(manifest_path)
    items = [item_from_manifest(raw) for raw in manifest["items"]]
    errors = preflight(items, manifest)
    if errors:
        for error in errors:
            print(f"PREFLIGHT FAILED: {error}", file=sys.stderr)
        return 1

    log_path = Path(args.log).expanduser()
    if not log_path.is_absolute():
        log_path = run_dir / log_path
    dry_run = args.dry_run or not args.execute
    failures = run_items(items, run_dir, mode, dry_run=dry_run, log_path=log_path)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
