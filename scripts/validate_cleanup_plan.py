#!/usr/bin/env python3
"""Validate a Disk Space Janitor cleanup plan before execution.

This script is a read-only dry-run validator. It does not delete, move,
compress, modify, create, or rewrite cleanup targets. It reads a JSON cleanup
plan, verifies that approved write actions still match exact paths under
approved prefixes, estimates current size, and reports a dry-run summary.
"""

from __future__ import annotations

import argparse
import json
import os
import stat
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


WRITE_ACTIONS = {"delete", "stage", "trash", "compress"}
REQUIRED_ITEM_FIELDS = {"id", "path", "type", "size_bytes", "risk", "proposed_action"}
DANGEROUS_NAMES = {"", ".", ".."}
TYPE_ALIASES = {
    "dir": "directory",
    "folder": "directory",
    "file": "file",
    "directory": "directory",
}


@dataclass
class ItemSummary:
    id: str
    path: str
    action: str
    expected_type: str
    actual_type: str | None
    expected_size_bytes: int
    current_size_bytes: int | None
    risk: str
    exists: bool
    reversible: str | None = None


def load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, dict):
        raise ValueError("Plan must be a JSON object.")
    return data


def resolve_path(raw: str) -> Path:
    if raw in DANGEROUS_NAMES:
        raise ValueError(f"Refusing empty or broad path: {raw!r}")
    path = Path(raw).expanduser()
    if any(part in DANGEROUS_NAMES for part in path.parts):
        raise ValueError(f"Refusing path with unsafe segment: {raw}")
    return path.resolve(strict=False)


def is_root_like(path: Path) -> bool:
    anchor = Path(path.anchor).resolve(strict=False) if path.anchor else None
    home = Path.home().resolve(strict=False)
    return path == anchor or path == home


def is_mount_point(path: Path) -> bool:
    try:
        return path.is_mount()
    except OSError:
        return False


def path_under(path: Path, prefixes: list[Path]) -> bool:
    for prefix in prefixes:
        try:
            path.relative_to(prefix)
            return True
        except ValueError:
            continue
    return False


def normalize_type(raw_type: Any) -> str:
    return TYPE_ALIASES.get(str(raw_type).lower(), str(raw_type).lower())


def actual_type(path: Path) -> str | None:
    try:
        info = path.lstat()
    except OSError:
        return None
    mode = info.st_mode
    if stat.S_ISLNK(mode):
        return "symlink"
    if stat.S_ISDIR(mode):
        return "directory"
    if stat.S_ISREG(mode):
        return "file"
    return "special"


def estimate_size(path: Path) -> tuple[int | None, list[str], int]:
    warnings: list[str] = []
    item_count = 0
    try:
        info = path.lstat()
    except OSError as error:
        return None, [f"Could not stat {path}: {error}"], item_count

    if stat.S_ISLNK(info.st_mode):
        return None, [f"Refusing to estimate symlink target: {path}"], item_count

    if stat.S_ISREG(info.st_mode):
        return info.st_size, warnings, 1

    if not stat.S_ISDIR(info.st_mode):
        return info.st_size, [f"Special file type encountered: {path}"], 1

    total = 0
    root_device = info.st_dev
    for current, dirs, files in os.walk(path, topdown=True, followlinks=False):
        current_path = Path(current)
        try:
            current_info = current_path.lstat()
        except OSError as error:
            warnings.append(f"Could not stat directory {current_path}: {error}")
            dirs[:] = []
            continue
        if current_path != path and current_info.st_dev != root_device:
            warnings.append(f"Skipped mounted path while estimating size: {current_path}")
            dirs[:] = []
            continue

        kept_dirs = []
        for name in dirs:
            child = current_path / name
            try:
                child_info = child.lstat()
            except OSError as error:
                warnings.append(f"Could not stat child directory {child}: {error}")
                continue
            if stat.S_ISLNK(child_info.st_mode):
                warnings.append(f"Skipped symlink while estimating size: {child}")
                continue
            kept_dirs.append(name)
        dirs[:] = kept_dirs

        for name in files:
            child = current_path / name
            try:
                child_info = child.lstat()
            except OSError as error:
                warnings.append(f"Could not stat file {child}: {error}")
                continue
            if stat.S_ISLNK(child_info.st_mode):
                warnings.append(f"Skipped symlink while estimating size: {child}")
                continue
            total += child_info.st_size
            item_count += 1
    return total, warnings, item_count


def validate_plan(plan: dict[str, Any]) -> dict[str, Any]:
    errors: list[str] = []
    warnings: list[str] = []
    summaries: list[ItemSummary] = []

    items = plan.get("items")
    if not isinstance(items, list) or not items:
        errors.append("Plan must include a non-empty items list.")
        return dry_run_result(False, errors, warnings, summaries)

    approved_prefixes_raw = plan.get("approved_prefixes", [])
    if not isinstance(approved_prefixes_raw, list):
        errors.append("approved_prefixes must be a list when provided.")
        approved_prefixes_raw = []

    approved_prefixes: list[Path] = []
    for raw_prefix in approved_prefixes_raw:
        try:
            prefix = resolve_path(str(raw_prefix))
        except ValueError as error:
            errors.append(f"Invalid approved prefix {raw_prefix!r}: {error}")
            continue
        if is_root_like(prefix):
            errors.append(f"Approved prefix is too broad: {prefix}")
        approved_prefixes.append(prefix)

    seen_ids: set[str] = set()
    write_count = 0
    expected_total = plan.get("expected_total_size_bytes")
    planned_total = 0
    current_total = 0
    total_item_count = 0
    allow_symlinks = bool(plan.get("allow_symlinks", False))
    allow_mount_points = bool(plan.get("allow_mount_points", False))

    for index, raw_item in enumerate(items, start=1):
        if not isinstance(raw_item, dict):
            errors.append(f"Item {index} must be an object.")
            continue
        missing = sorted(REQUIRED_ITEM_FIELDS - raw_item.keys())
        if missing:
            errors.append(f"Item {index} missing required fields: {', '.join(missing)}")
            continue

        item_id = str(raw_item["id"])
        if item_id in seen_ids:
            errors.append(f"Duplicate item id: {item_id}")
        seen_ids.add(item_id)

        action = str(raw_item["proposed_action"]).lower()
        if action in WRITE_ACTIONS:
            write_count += 1
        else:
            warnings.append(f"Item {item_id} has non-write action {action!r}; it will not be counted as approved cleanup.")
            continue

        expected_type = normalize_type(raw_item["type"])
        try:
            target = resolve_path(str(raw_item["path"]))
        except ValueError as error:
            errors.append(f"Item {item_id} has invalid path: {error}")
            continue

        if is_root_like(target):
            errors.append(f"Item {item_id} targets a broad root: {target}")

        if approved_prefixes and not path_under(target, approved_prefixes):
            errors.append(f"Item {item_id} is outside approved prefixes: {target}")

        target_exists = target.exists() or target.is_symlink()
        found_type = actual_type(target)
        if not target_exists:
            errors.append(f"Item {item_id} target no longer exists: {target}")

        if found_type == "symlink" and not allow_symlinks:
            errors.append(f"Item {item_id} is a symlink and must not be followed: {target}")

        if is_mount_point(target) and not allow_mount_points:
            errors.append(f"Item {item_id} is a mount point and requires explicit mount approval: {target}")

        if found_type is not None and expected_type in {"file", "directory"} and found_type != expected_type:
            errors.append(f"Item {item_id} type changed: expected {expected_type}, found {found_type}")

        risk = str(raw_item["risk"]).lower()
        if risk in {"high", "unknown"}:
            warnings.append(f"Item {item_id} is {risk} risk; require explicit final confirmation.")

        try:
            planned_size = int(raw_item["size_bytes"])
            planned_total += planned_size
        except (TypeError, ValueError):
            errors.append(f"Item {item_id} has non-integer size_bytes.")
            planned_size = 0

        current_size, size_warnings, item_count = estimate_size(target) if target_exists else (None, [], 0)
        warnings.extend(f"Item {item_id}: {warning}" for warning in size_warnings)
        if current_size is not None:
            current_total += current_size
        total_item_count += item_count
        if current_size is not None and planned_size:
            tolerance = max(1024 * 1024, int(planned_size * 0.05))
            if abs(current_size - planned_size) > tolerance:
                warnings.append(
                    f"Item {item_id} current size differs from plan: planned {planned_size}, current {current_size}"
                )

        summaries.append(
            ItemSummary(
                id=item_id,
                path=str(target),
                action=action,
                expected_type=expected_type,
                actual_type=found_type,
                expected_size_bytes=planned_size,
                current_size_bytes=current_size,
                risk=risk,
                exists=target_exists,
                reversible=raw_item.get("reversible"),
            )
        )

    expected_count = plan.get("expected_count")
    if expected_count is not None and int(expected_count) != write_count:
        errors.append(f"expected_count mismatch: expected {expected_count}, write actions {write_count}")

    if expected_total is not None and int(expected_total) != planned_total:
        errors.append(f"expected_total_size_bytes mismatch: expected {expected_total}, planned items total {planned_total}")

    return dry_run_result(not errors, errors, warnings, summaries, current_total, planned_total, write_count, total_item_count)


def dry_run_result(
    ok: bool,
    errors: list[str],
    warnings: list[str],
    summaries: list[ItemSummary],
    current_total: int = 0,
    planned_total: int = 0,
    write_count: int = 0,
    total_item_count: int = 0,
) -> dict[str, Any]:
    return {
        "ok": ok,
        "dry_run": True,
        "write_actions": write_count,
        "planned_size_bytes": planned_total,
        "current_size_bytes": current_total,
        "estimated_reclaimable_bytes": current_total,
        "estimated_item_count": total_item_count,
        "unexpected_paths_found": bool(errors),
        "items": [asdict(item) for item in summaries],
        "errors": errors,
        "warnings": warnings,
    }



def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Validate a Disk Space Janitor cleanup plan JSON file.")
    parser.add_argument("--plan", required=True, help="Path to cleanup plan JSON.")
    parser.add_argument("--json", action="store_true", help="Emit JSON result.")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        plan = load_json(Path(args.plan))
        result = validate_plan(plan)
    except Exception as error:
        result = dry_run_result(False, [str(error)], [])

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print("OK" if result["ok"] else "FAILED")
        print(f"Dry-run: {result['write_actions']} write action(s), current size {result['current_size_bytes']} bytes")
        print(f"Unexpected paths found: {'yes' if result['unexpected_paths_found'] else 'none'}")
        for warning in result["warnings"]:
            print(f"WARNING: {warning}")
        for error in result["errors"]:
            print(f"ERROR: {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
