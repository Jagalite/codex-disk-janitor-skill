from __future__ import annotations

import json
import shutil
import subprocess
import sys
import unittest
import uuid
from contextlib import contextmanager
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
SCAN_SCRIPT = REPO_ROOT / "scripts" / "scan_metadata.py"
VALIDATE_SCRIPT = REPO_ROOT / "scripts" / "validate_cleanup_plan.py"
TEST_TMP_ROOT = REPO_ROOT / ".test-tmp"


def run_json(args: list[str]) -> tuple[int, dict]:
    result = subprocess.run(args, capture_output=True, text=True, check=False)
    try:
        payload = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise AssertionError(f"Expected JSON stdout, got: {result.stdout!r}\nstderr: {result.stderr!r}") from error
    return result.returncode, payload


def write_plan(path: Path, plan: dict) -> None:
    path.write_text(json.dumps(plan), encoding="utf-8")


@contextmanager
def temp_dir():
    TEST_TMP_ROOT.mkdir(exist_ok=True)
    path = TEST_TMP_ROOT / f"case-{uuid.uuid4().hex}"
    path.mkdir()
    try:
        yield str(path)
    finally:
        shutil.rmtree(path, ignore_errors=True)


class ScanMetadataTests(unittest.TestCase):
    def test_normal_metadata_scan_reports_file(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "large.bin"
            target.write_bytes(b"x" * 128)

            code, payload = run_json([sys.executable, str(SCAN_SCRIPT), "--root", str(root), "--json"])

            self.assertEqual(code, 0)
            report = payload["reports"][0]
            self.assertFalse(report["partial"])
            self.assertEqual(report["scanned_files"], 1)
            self.assertEqual(report["largest_files"][0]["path"], str(target.resolve()))

    def test_hidden_files_skipped_by_default(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            hidden = root / ".cache"
            hidden.mkdir()
            (hidden / "item.bin").write_bytes(b"x")

            _, payload = run_json([sys.executable, str(SCAN_SCRIPT), "--root", str(root), "--json"])

            report = payload["reports"][0]
            self.assertEqual(report["hidden_skipped_count"], 1)
            self.assertEqual(report["hidden_skipped_directories_count"], 1)
            self.assertEqual(report["scanned_files"], 0)

    def test_hidden_files_included_when_approved(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            hidden = root / ".cache"
            hidden.mkdir()
            (hidden / "item.bin").write_bytes(b"x")

            _, payload = run_json(
                [sys.executable, str(SCAN_SCRIPT), "--root", str(root), "--include-hidden", "--json"]
            )

            report = payload["reports"][0]
            self.assertEqual(report["hidden_skipped_count"], 0)
            self.assertEqual(report["scanned_files"], 1)

    def test_symlink_skipped(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            target.write_text("data", encoding="utf-8")
            link = root / "link.txt"
            try:
                link.symlink_to(target)
            except OSError as error:
                self.skipTest(f"Symlink creation is unavailable: {error}")

            _, payload = run_json([sys.executable, str(SCAN_SCRIPT), "--root", str(root), "--json"])

            report = payload["reports"][0]
            self.assertIn(str(link), report["skipped_links"])

    def test_root_symlink_rejected(self) -> None:
        with temp_dir() as tmp:
            base = Path(tmp)
            target = base / "target"
            target.mkdir()
            link = base / "root-link"
            try:
                link.symlink_to(target, target_is_directory=True)
            except OSError as error:
                self.skipTest(f"Symlink creation is unavailable: {error}")

            _, payload = run_json([sys.executable, str(SCAN_SCRIPT), "--root", str(link), "--json"])

            report = payload["reports"][0]
            self.assertTrue(report["partial"])
            self.assertIn("Root is a symlink", report["partial_reasons"][0])

    def test_drive_root_rejected_by_default(self) -> None:
        drive_root = Path(Path.cwd().anchor)
        _, payload = run_json([sys.executable, str(SCAN_SCRIPT), "--root", str(drive_root), "--json"])

        report = payload["reports"][0]
        self.assertTrue(report["partial"])
        self.assertTrue(any("root" in reason for reason in report["partial_reasons"]))


class ValidateCleanupPlanTests(unittest.TestCase):
    def base_plan(self, root: Path, item_path: Path, item_type: str = "file", size: int = 4) -> dict:
        return {
            "requested_scope": str(root),
            "approved_scope": str(root),
            "generated_at": "2026-04-24T12:00:00Z",
            "approval_required": True,
            "approved_item_ids": ["1.1"],
            "approval_phrase": "Approved to trash ID 1.1 only",
            "approved_prefixes": [str(root)],
            "expected_count": 1,
            "expected_total_size_bytes": size,
            "items": [
                {
                    "id": "1.1",
                    "path": str(item_path),
                    "type": item_type,
                    "size_bytes": size,
                    "risk": "low",
                    "proposed_action": "trash",
                    "reversible": "Usually, until trash is emptied",
                }
            ],
        }

    def validate(self, plan: dict) -> tuple[int, dict]:
        with temp_dir() as tmp:
            plan_path = Path(tmp) / "plan.json"
            write_plan(plan_path, plan)
            return run_json([sys.executable, str(VALIDATE_SCRIPT), "--plan", str(plan_path), "--json"])

    def test_outside_approved_prefix_rejected(self) -> None:
        with temp_dir() as tmp:
            base = Path(tmp)
            approved = base / "approved"
            outside = base / "outside.txt"
            approved.mkdir()
            outside.write_bytes(b"data")
            plan = self.base_plan(approved, outside)

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("outside approved prefixes" in error for error in payload["errors"]))

    def test_symlink_target_rejected(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            link = root / "link.txt"
            target.write_text("data", encoding="utf-8")
            try:
                link.symlink_to(target)
            except OSError as error:
                self.skipTest(f"Symlink creation is unavailable: {error}")
            plan = self.base_plan(root, link)

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("symlink" in error for error in payload["errors"]))

    def test_changed_type_rejected(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "folder"
            target.mkdir()
            plan = self.base_plan(root, target, item_type="file", size=0)

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("type changed" in error for error in payload["errors"]))

    def test_duplicate_item_ids_rejected(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            first = root / "first.txt"
            second = root / "second.txt"
            first.write_bytes(b"data")
            second.write_bytes(b"more")
            plan = self.base_plan(root, first)
            plan["items"].append({**plan["items"][0], "path": str(second)})
            plan["expected_count"] = 2
            plan["expected_total_size_bytes"] = 8

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("Duplicate item id" in error for error in payload["errors"]))

    def test_expected_count_mismatch_rejected(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            target.write_bytes(b"data")
            plan = self.base_plan(root, target)
            plan["expected_count"] = 2

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("expected_count mismatch" in error for error in payload["errors"]))

    def test_expected_total_mismatch_rejected(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            target.write_bytes(b"data")
            plan = self.base_plan(root, target)
            plan["expected_total_size_bytes"] = 999

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("expected_total_size_bytes mismatch" in error for error in payload["errors"]))

    def test_missing_approval_metadata_rejected(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            target.write_bytes(b"data")
            plan = self.base_plan(root, target)
            del plan["approval_phrase"]

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("approval metadata" in error for error in payload["errors"]))

    def test_compression_requires_safeguards(self) -> None:
        with temp_dir() as tmp:
            root = Path(tmp)
            target = root / "target.txt"
            target.write_bytes(b"data")
            plan = self.base_plan(root, target)
            plan["items"][0]["proposed_action"] = "compress"
            plan["approval_phrase"] = "Approved to compress ID 1.1 only"

            code, payload = self.validate(plan)

            self.assertEqual(code, 1)
            self.assertTrue(any("Compression item 1.1 missing required fields" in error for error in payload["errors"]))


if __name__ == "__main__":
    unittest.main()
