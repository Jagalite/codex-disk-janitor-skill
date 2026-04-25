# Disk Space Janitor Skill

A Codex skill for safely finding disk-space cleanup opportunities.

The skill focuses on identification, triage, review, and auditable cleanup planning. It does not encourage blind deletion. The default flow is metadata-first scanning, risk labeling, exact item review, optional staging/compression, dry-run, final confirmation, and logging.

## Disclaimer

This skill is provided as-is, without warranty. Disk cleanup can cause data loss if used incorrectly. Users are responsible for reviewing all proposed actions, maintaining backups, and deciding whether to execute any staging, trash, deletion, or compression operation. This project is designed to reduce risk through scoped scans, dry-runs, confirmations, and logs, but it cannot guarantee that any file is safe to remove.

## What It Does

- Finds large files, large folders, stale downloads, caches, build artifacts, and known cleanup locations.
- Marks reports as complete or partial when caps, skipped paths, or access issues affect results.
- Supports fast top-level folder summaries for broad folders.
- Offers optional content-aware review only after user approval.
- Builds an interactive cleanup draft before any write action.
- Supports staging under `CodexJanitor/<run-id>/`.
- Supports compression with expiry review dates.
- Uses generated cleanup scripts with self-test, dry-run, preflight checks, and logs.

## Install

Copy the skill folder into your Codex skills directory:

```powershell
Copy-Item -Recurse .\disk-space-janitor "$env:USERPROFILE\.codex\skills\disk-space-janitor"
```

Then start a fresh Codex thread and invoke:

```text
Use $disk-space-janitor to inspect this workspace for cleanup opportunities. Do not delete anything.
```

You can also test directly by path without installing:

```text
Use the skill at <path-to-this-repo>\disk-space-janitor to inspect this workspace for cleanup opportunities. Do not delete anything.
```

## Test Locally

Run the read-only scanner against the skill folder:

```powershell
python .\disk-space-janitor\scripts\space_inventory.py --root .\disk-space-janitor --summary-mode top-level --top 10 --format markdown
```

Run the cleanup template self-test. This creates fake files only under the provided run folder:

```powershell
python .\disk-space-janitor\scripts\cleanup_template.py --run-dir .\CodexJanitor\template-self-test --self-test
```

The `.gitignore` excludes local `CodexJanitor/` run folders and generated cleanup artifacts.

## Scanner

`disk-space-janitor/scripts/space_inventory.py` is read-only.

Useful options:

- `--summary-mode top-level`: size immediate children of the root.
- `--format json`: manifest-friendly output with exact byte counts.
- `--progress-seconds 5`: periodic progress updates for long scans.
- `--max-files N`: cap file traversal and mark reports partial when reached.
- `--size-known-locations`: estimate common cleanup folder sizes.

Human-readable sizes use binary units such as `MiB` and `GiB`; JSON size fields are bytes.

## Cleanup Template

`disk-space-janitor/scripts/cleanup_template.py` is a reusable starting point for generated cleanup scripts.

It supports:

- `--self-test`
- `--dry-run`
- `--stage`
- `--trash`
- `--delete`
- `--execute`
- exact-path manifest loading
- preflight checks
- JSONL logging
- Windows Recycle Bin behavior

Write modes dry-run unless `--execute` is passed. Actual write actions should only happen after the user approves exact items and reviews dry-run output.

## Safety Model

The skill is intentionally conservative:

- Metadata scan first.
- Content inspection only after approval.
- Exact filenames and full paths before cleanup.
- Interactive cleanup draft before execution.
- Staging offered before deletion.
- Compression treated as preservation, not automatic cleanup.
- Generated scripts default to dry-run.
- Self-tests use fake files.
- Final write actions require confirmation.
- Logs preserve original paths for backout or restore.

## Privacy

Avoid committing local cleanup outputs. The repo ignores:

- `CodexJanitor/`
- generated manifests/logs/plans
- generated `cleanup.py`
- Python caches

Do not commit scan reports that contain personal filenames, app names, game titles, media names, or local paths.

The skill defaults to a high-sensitivity privacy posture. It should not infer whether a machine is personal, work, school, shared, or managed from installed apps, games, filenames, folder names, browser profiles, or media. If that context would materially improve safety or recommendations, Codex should ask the user directly and use the answer only to adjust caution.
