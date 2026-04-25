---
name: disk-space-janitor
description: Safely audit disk usage and prepare reviewable cleanup plans. Use when the user asks to find large files, understand disk usage, identify cleanup candidates, classify cleanup risk, inspect selected files for importance, or draft disk cleanup actions. Starts read-only and metadata-only. Do not use for general code cleanup, refactoring, or formatting. Never delete, move, compress, truncate, rewrite, or modify files unless the user explicitly approves a final exact-path cleanup draft after dry-run.
---

# Disk Space Janitor Skill

## Purpose

Help users find disk-space cleanup opportunities safely. The agent should audit storage usage, identify likely cleanup candidates, classify risk, and produce reviewable cleanup plans. The skill is conservative by design and should favor user review, auditability, and least-destructive options.

## Core Rule

The default mode is read-only. Never delete, move, compress, truncate, rewrite, or modify files unless the user explicitly approves a final cleanup draft.

Do not treat broad cleanup requests as permission to write. If the user asks to "clean up" or "free space," start with read-only inspection and cleanup planning.

## Default Workflow

1. Confirm scope.
2. Start with metadata-only scan.
3. Summarize disk usage and likely cleanup candidates.
4. Classify candidates by risk.
5. Ask before inspecting file contents.
6. Produce a cleanup draft before write actions.
7. Run a dry-run before execution.
8. Execute only the approved actions.
9. Verify results.
10. Write or present an audit log.

## Scope Defaults

If scope is ambiguous, ask for an exact path or named app/tool scope before scanning. Do not scan home roots, drive roots, system roots, cloud-sync roots, mounted volumes, network shares, or broad parent directories unless the user explicitly names that scope.

For requests like "clean up my machine" or "find space anywhere," propose a staged approach:

1. Ask which folder, drive, workspace, or app/tool area to inspect first.
2. Start with a top-level metadata summary.
3. Mark the report partial when the user-approved scope excludes likely relevant locations.
4. Ask again before expanding scope.

## Metadata-First Scan

Inspect metadata before content. Useful metadata includes:

- Path.
- File or directory type.
- Size.
- Modified time.
- Access time if available, with a warning that it may be disabled, unreliable, or updated by scans.
- Item count for directories.
- Apparent category such as cache, build artifact, installer, archive, media, document, source tree, package cache, VM image, database, log, or temp file.

For long scans, provide concise progress updates. Include current scope, elapsed time, approximate files/directories scanned, largest candidates found so far, and whether any limits or access errors make the report partial. Do not stream every path.

## Safe Scan Procedure

When scanning a scope:

1. Resolve the user-approved scope to an absolute path.
2. Reject empty paths, drive roots, home/profile roots, workspace roots, system roots, mounted volumes, and cloud-sync roots unless the user explicitly approved that exact scope.
3. Use metadata-only operations first: `lstat`, directory entry type, size, modified time, and item counts.
4. Do not follow symlinks, junctions, reparse points, bind mounts, network shares, or mounted volumes by default.
5. Do not compute content hashes, read archive listings, parse logs, extract EXIF, preview media, inspect source files, or open documents without content-inspection approval.
6. Cap traversal by depth, item count, elapsed time, or top-N largest results when needed.
7. Report permission errors, skipped paths, traversal limits, and whether the scan is partial.
8. Prefer summaries by category first; expose exact paths when producing candidate tables or cleanup drafts.

Prefer `scripts/scan_metadata.py` for deterministic metadata scans when a local Python runtime is available. It follows this procedure by using `lstat`, avoiding symlinks by default, marking mount-like boundaries where detectable, capping traversal, and emitting JSON.

Example read-only scan:

```bash
python scripts/scan_metadata.py --root "<approved-path>" --max-files 200000 --max-depth 6 --json
```

If you use shell commands instead, keep them read-only, scoped to exact approved paths, and avoid broad recursive path dumps. Do not improvise destructive cleanup commands during scanning.

By default, the scanner skips dotfiles and dotdirectories such as `.git`. Use `--include-hidden` only when the user explicitly approves hidden file inspection.

Safe scan output should preserve:

- Requested root.
- Whether the scan is complete or partial.
- Partial reasons.
- Files and directories scanned.
- Skipped links, mount points, and access-denied paths.
- Skipped hidden paths unless hidden inspection was approved.
- Largest candidate files/directories.
- Category and extension summaries.

## Privacy Rules

Do not infer whether the machine is personal, work, school, shared, or managed from installed apps, games, filenames, folders, browser profiles, media, or project names.

If that context matters, ask the user directly. Use the answer only to adjust caution.

Do not inspect file contents without approval. When content inspection is approved, inspect only the selected files or folders and summarize signals without exposing sensitive content unless the user asks.

Hashing file contents, reading archive manifests, previewing media metadata, extracting EXIF, reading thumbnails, opening logs, parsing documents, and duplicate-content hashing count as content inspection unless the user explicitly approves them.

## Risk Taxonomy

Use these risk levels consistently. Read `references/risk-taxonomy.md` for examples.

- `Low risk`: Usually generated, cache-like, temporary, or easy to recreate. Still requires user review before write actions.
- `Medium risk`: Often removable after review, but may cost time, bandwidth, settings, history, or recovery effort.
- `High risk`: User data, app state, source, synced data, backups, or data with meaningful loss potential. Default to keep/manual review.
- `Unknown`: Purpose or ownership is unclear. Default to keep/manual review.

High risk and unknown items should default to keep/manual review.

## Never Delete Without Explicit Approval

Never delete these without exact-path review, a cleanup draft, dry-run, and explicit final approval:

- Source code.
- `.git` directories.
- `.env` files.
- Credentials, keys, tokens, password stores, or secrets.
- Databases.
- VM images.
- Photos, videos, audio, and media libraries.
- Documents, notes, PDFs, mail, or messages.
- Financial, legal, tax, identity, medical, school, or work files.
- Cloud-sync folders.
- Mounted volumes.
- Docker volumes.
- Backups.
- Application state/config.
- User-created archives.

If the user asks to delete one of these categories, slow down, show a clear warning, and ask for explicit final confirmation after the dry-run.

## Symlink, Mount, and Cloud-Sync Safety

- Do not follow symlinks by default.
- Detect symlinks, junctions, reparse points, and mounted paths where practical.
- Treat network shares, NAS paths, WSL mounts, external drives, Docker bind mounts, and cloud-sync folders as higher risk.
- Warn that deleting cloud-sync files may delete remote copies.
- Treat paths inside mounted or mapped storage as belonging to that storage, not merely to the visible parent folder.
- Reject unexpected path expansion during cleanup execution.

## Cleanup Draft Requirements

Before any write action, show a cleanup draft with:

- Exact paths.
- Action for each path.
- Estimated reclaimed size.
- Risk label.
- Reason.
- What will be left unchanged.
- Dry-run command or procedure.
- Reversibility or rollback notes.
- Audit log destination if applicable.

Use stable IDs so the user can approve or revise individual items.

## Execution Requirements

Before execution:

- Verify approved scope.
- Verify exact paths.
- Perform dry-run.
- Reject unexpected path expansion.
- Avoid following symlinks.
- Prefer quarantine, staging, or system trash over permanent deletion.
- Execute only approved actions.
- Verify result after execution.
- Summarize reclaimed size.

If anything differs from the approved cleanup draft, stop and ask. If deletion partially succeeds, rescan the approved target, report remaining size, update the audit log, and produce a follow-up plan for remnants.

Writing an audit log is itself a write action. If writing a local log was not explicitly approved, present the audit log in chat. If writing locally, use a user-approved destination.

When a cleanup plan is represented as JSON, prefer `scripts/validate_cleanup_plan.py` before dry-run or execution. It performs no writes. It rejects empty paths, roots and broad parent paths, traversal outside approved scope, symlinks unless explicitly allowed, mount points unless explicitly allowed, missing paths, type changes, and unexpected expansion. It estimates current size and outputs a dry-run summary. Validation is not permission to execute; it is only a preflight check.

## Output Style

Use concise tables for candidates and cleanup drafts. Include enough detail for informed review without dumping sensitive path lists unnecessarily.

Candidate table columns should usually include:

| ID | Path | Type | Size | Risk | Reason | Suggested next step |
| --- | --- | --- | --- | --- | --- | --- |

Cleanup draft table columns should usually include:

| ID | Path | Type | Size | Risk | Proposed action | Reversible? |
| --- | --- | --- | --- | --- | --- | --- |

Use clear warnings for high-risk actions. Never bury destructive actions in prose. Keep final approval requests short, explicit, and tied to exact item IDs and paths.

## Supporting References

- `references/safety-model.md`: safety philosophy.
- `references/risk-taxonomy.md`: risk levels and examples.
- `references/cleanup-plan-format.md`: cleanup draft format.
- `references/os-notes.md`: OS-specific cautions.
- `examples/`: sample safe workflows.
- `scripts/scan_metadata.py`: deterministic read-only metadata scanner.
- `scripts/validate_cleanup_plan.py`: cleanup plan structure and path validator.
