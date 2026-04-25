---
name: disk-space-janitor
description: Safe disk-space cleanup workflow for identifying large files, stale downloads, caches, build artifacts, duplicate-looking data, backups, app/system cleanup opportunities, and optional content-aware importance ranking for text files, PDFs, scripts, images, audio, or videos on a user's computer. Use when Codex is asked to free up disk space, find what is taking space, audit storage usage, clean a computer, reduce disk pressure, inspect whether large files matter, or prepare deletion recommendations. The skill emphasizes metadata-first identification, opt-in content inspection, triage, user confirmation, OS-native cleanup tools, and non-destructive reporting; Codex must not delete user files automatically.
---

# Disk Space Janitor

## Core Rule

Identify and prioritize cleanup opportunities. Do not delete files, empty trash, uninstall apps, purge caches, or run destructive cleanup commands unless the user explicitly asks for a specific action after reviewing the candidates.

Prefer producing a deletion plan with exact paths, risk labels, expected reclaimed space, and manual/OS-native steps. When deletion is appropriate, steer the user toward built-in cleanup tools or explicit commands they can review.

## Startup Notice

At the start of a cleanup session, briefly remind the user that disk cleanup can cause data loss, the workflow is best-effort and review-driven, and no files will be deleted or modified without their explicit approval. Keep this notice short and do not repeat it unless the user moves from read-only scanning to write actions.

## Permission Model

Start with the least access needed and escalate only when the user approves a broader scope.

Permission levels:

- `workspace`: Inspect only the current workspace or repository. Use for project bloat, build artifacts, dependency folders, and skill testing.
- `selected folders`: Inspect user-provided roots such as Downloads, Desktop, Documents, a media folder, or a project folder. This is the normal cleanup mode.
- `home read-only`: Inspect the user's home/profile folder broadly. Ask first because paths and filenames can reveal private information.
- `drive/root read-only`: Inspect a drive root or multiple system-wide locations for a full-machine inventory. Ask for explicit higher access, keep the scan read-only, avoid following symlinks, and summarize findings instead of dumping long path lists.
- `protected/system read-only`: Inspect system or admin-sensitive locations only when the user explicitly asks for deeper diagnostics. Prefer OS-native cleanup tools over manual file advice.
- `write/delete`: Treat as a separate post-report action. Require the user to choose exact targets after Phase 3; prefer reversible moves to the system trash or a staging folder.

For a full scan, tell the user that broader read access is needed to inspect drive roots, user profiles, app data, caches, and possibly protected/system locations. Make clear that the scan is read-only and that content inspection and deletion remain separate approvals.

## Context And Privacy Posture

Default to a high-sensitivity cleanup posture for every machine. Do not infer whether the computer is personal, work, school, shared, or managed from filenames, installed apps, games, browser profiles, folder names, or media.

If the context would materially improve safety or recommendations, ask the user directly:

```text
Is this a personal, work, school, shared, or managed computer? This only changes how cautious I should be with recommendations; I will not inspect contents or delete anything without approval.
```

Use the answer only to adjust caution:

- For work, school, shared, or managed computers, be stricter about app data, credentials, logs, sync folders, admin-managed software, company/school files, and installed applications.
- For personal computers, still protect documents, media, account data, source repositories, backups, and app profiles.
- For mixed-use machines, apply the stricter posture.

Never use the privacy posture to justify automatic deletion or content inspection.

## Workflow

1. Establish scope:
   - Ask for the target drive/folder only if the user has not provided one and scanning the whole home directory would be too broad.
   - Use the permission model to decide whether the request fits workspace, selected-folder, home, drive/root, protected/system, or write/delete access.
   - Confirm whether the user wants a quick scan, a deep scan, or app-specific investigation.
   - Note privacy: filenames can reveal sensitive information; summarize before sharing long path lists.

2. Inventory space:
   - Use OS-native commands for high-level disk usage when available.
   - Use `scripts/space_inventory.py` for a safe, read-only scan of specific roots.
   - Avoid scanning system-protected directories without a reason.
   - Do not follow symlinks by default.
   - For broad scans, use subagents only for parallel read-only investigation of separate scopes.
   - For scans lasting more than 5 seconds, provide concise progress updates with current root, phase, files/directories scanned, largest candidates found so far, skipped/protected areas, and whether limits were reached. Do not dump sensitive filenames during progress updates.

3. Classify candidates:
   - Read `references/cleanup-taxonomy.md` when deciding risk categories, cleanup methods, or OS-specific locations.
   - Label each candidate as `low`, `medium`, or `high` risk.
   - Separate user-created files from caches, build outputs, installers, logs, backups, VM/container images, and package-manager artifacts.

4. Offer content-aware review:
   - Ask before opening personal files, PDFs, text documents, source files, media, exports, logs, or archives to rank importance.
   - Explain that content inspection can improve recommendations but may expose sensitive information.
   - Inspect only the selected files or folders the user approves.
   - Summarize signals and risk without quoting sensitive content unless the user asks.
   - Use subagents only when the approved scope can be split cleanly by file group or folder.

5. Report findings:
   - Lead with the largest low-risk wins.
   - Clearly mark reports as `complete` or `partial`; explain caps, access-denied paths, skipped links, and known-location size limits.
   - Include estimated space, path, why it is probably safe or risky, and the recommended cleanup method.
   - For personal files, recommend review/archive/move instead of deletion.
   - Offer compression with an expiry review date for old but not obviously disposable user files.
   - For application data, prefer the app's own cleanup UI.

6. Deletion handoff:
   - Ask the user to choose specific items or categories.
   - If asked to delete, restate the exact targets, risk, and whether the operation is reversible.
   - Show exact filenames and full paths before final approval; do not confirm deletion from group summaries alone.
   - Build an interactive draft cleanup plan so the user can choose item-by-item actions before execution.
   - Offer a staging folder for any exact selected item before deletion, and especially recommend it for user-created or ambiguous files.
   - Offer compression as an alternative when it meaningfully saves space and preserves data.
   - For multiple items or mixed-risk actions, copy/adapt `scripts/cleanup_template.py` into `CodexJanitor/<run-id>/cleanup.py` instead of using ad hoc shell commands.
   - Before write actions, run preflight checks for free space, access-control/read-only issues, symlinks or special filesystem links, protected children, active files, and expected item counts/sizes.
   - If a write action needs higher filesystem access outside the workspace, explain the reason and request the narrowest permission needed.
   - Prefer reversible cleanup actions over permanent deletion.
   - Log every cleanup action with target path, estimated size, description, method, timestamp, reversibility, and outcome.
   - After write actions, rescan affected targets and reconcile removed, remaining, skipped, and failed items.
   - Never use recursive force deletion on broad or computed paths.

## Content-Aware Review

Use content inspection only after the metadata scan and user approval. Ask a concise question such as: "Do you want me to inspect the contents of these selected files to rank importance? This may reveal sensitive text or media."

Rank importance with conservative defaults:

- `probably disposable`: generated files, dependency folders, cache files, build outputs, downloaded installers, empty or machine-generated logs.
- `review first`: archives, exports, duplicate-looking files, old scripts, PDFs from Downloads, large media, notebooks, local databases.
- `protect`: personal documents, legal/financial/medical/work records, photos/videos/audio with personal content, source repositories, credentials, config files, app profiles, cloud-sync data.

For text/PDF/script review:

- Prefer metadata, folder context, headings, file structure, and short summaries over full content disclosure.
- Treat source files in active repositories as high importance unless they are generated, vendored, or build artifacts.
- Treat logs as medium risk when they may contain tokens, paths, emails, or debugging history.
- Treat PDFs as high risk when they appear personal, contractual, financial, medical, legal, or work-related.

For images/videos/audio:

- Use available vision tools, metadata, thumbnails, representative video frames, transcripts, or duration/codec information when available.
- Do not infer that personal media is backed up or unimportant.
- For video, inspect representative frames rather than claiming continuous viewing unless the environment supports it.
- For audio, prefer metadata and transcription when available; otherwise classify from path, size, and user context only.

## Subagents

Use subagents for large or multi-area cleanup requests when parallel read-only work will help. Keep each task bounded to a folder, category, or file type, and tell the subagent to return privacy-preserving findings by default: category, approximate size, risk, confidence, and recommended cleanup method. Ask for exact paths only for user-approved candidate items or a bounded exact-path review.

Good subagent scopes:

- Downloads, Desktop, Documents, or another user-approved folder.
- Development artifacts such as `node_modules`, `target`, `.venv`, build folders, and caches.
- App/system cleanup locations that can be inspected without administrator privileges.
- Docker, VM, game, or media-heavy folders as read-only investigations.
- Approved content-aware review for selected PDFs/text files, source/script folders, logs/exports, or media metadata/frames.

Do not use subagents for deletion, emptying trash, uninstalling apps, pruning Docker/VM data, administrator-level cleanup, or any irreversible operation. The main agent must synthesize the final report, ask the user to choose actions, and own any explicit deletion handoff.

## Safe Commands

Use read-only discovery commands first after the user approves a scan scope. Prefer top-level summaries before recursive file listings, and avoid printing full filenames/paths until the user asks to inspect exact candidates.

```bash
df -h
du -hd 1 "<approved-folder>" 2>/dev/null | sort -h
```

Prefer the bundled scanner for structured reports:

```bash
python scripts/space_inventory.py --root "<approved-folder>" --max-depth 4 --top 30 --format markdown
```

Add `--size-known-locations` only when the user is comfortable with a slower scan of common cleanup folders such as Downloads and caches.
Add `--progress-seconds 5` for scans where progress updates are useful.
Use `--summary-mode top-level` when the user needs a fast immediate-child folder size summary without listing every file in the final report.
Use `--format json` when generating a cleanup manifest or planner input; JSON size fields are exact bytes and Markdown human sizes use binary units such as MiB/GiB.

## Scan Modes And Partial Results

For broad folders such as Downloads, Documents, Projects, app data, game libraries, and app install folders, prefer starting with:

```bash
python scripts/space_inventory.py --root "<folder>" --summary-mode top-level --top 50 --progress-seconds 10
```

Use full inventory mode after the top-level summary identifies promising subfolders.

Reports must state whether they are partial. Treat a report as partial when any scan hits:

- `--max-files`.
- A per-folder or known-location sizing cap.
- Access denied, stat failures, read errors, skipped protected areas, symlinks, or special filesystem links.
- User-selected scope limits that exclude relevant sibling folders.

For full-drive scans or huge folders, provide checkpoint summaries or streaming partial results before the scan completes. A checkpoint should be compact: current phase, elapsed time, root, files/directories scanned, largest directories so far, cap status, and next likely useful root. Do not stream every path.

## Last Used View

When the user asks what has not been used recently, provide a metadata-only view:

- Folder creation time.
- Folder last write time.
- Newest internal file write time.
- Oldest/newest large file write times when useful.
- Last access time only with a warning that it may be disabled, unreliable, or updated by scans.

Do not treat old timestamps as proof that personal files are unimportant.

## App-Managed Cleanup

For app-managed locations, prefer uninstallers, app-native cleanup, package-manager cleanup, or vendor tools before filesystem deletion. Direct filesystem deletion can reclaim space but may leave app state inconsistent or make later updates, repairs, or uninstalls harder. If direct deletion is still considered, require exact paths, app-closed confirmation, reversible options where applicable, preflight checks, and a final confirmation.

## Output Pattern

Use this structure for user-facing cleanup reports:

- Storage summary: total/free space if known, roots scanned, scan limits.
- Best candidates: top low-risk items with estimated reclaimed space.
- Optional content-aware findings: only for files the user approved for inspection.
- Review before deleting: personal files, backups, archives, duplicate-looking folders.
- Avoid deleting: OS files, active app databases, source-controlled worktrees, unknown config directories.
- Next actions: exact manual steps or commands, grouped by risk.

For deletion or staging approval, expand selected groups into exact items before asking for final confirmation:

```text
[1.1] filename.ext
      Path: C:\full\path\filename.ext
      Size: 105 MB
      Description: Old installer in Downloads
      Risk: low
      Planned action: move to staging folder
```

Use stable item IDs such as `1.1`, `1.2`, and ask the user to confirm exact IDs.

## Interactive Cleanup Planner

Treat Phase 3 as an editable cleanup plan. Do not jump from findings directly to execution.

Create a draft plan with stable item IDs and one proposed action per item:

- `keep`
- `stage`
- `compress`
- `trash`
- `delete`
- `skip`
- `inspect`

For each item, show filename, full original path, estimated size, description, risk, proposed action, and reversibility. Group items for readability, but keep item IDs stable across revisions.

Let the user revise the draft with plain-language commands:

- "stage 1.1 1.2"
- "keep all PDFs"
- "compress the logs"
- "remove 2.4 from the plan"
- "show details for high risk items"
- "change downloads to trash except the PDFs"

After each revision, show a concise updated summary:

- item count by action
- estimated size by action
- path prefixes
- extension counts
- risk distribution
- largest items
- recursive folders included
- cross-volume/share warnings
- script, manifest, archive, staging, and log paths

Before execution, produce a final draft and ask for confirmation of exact item IDs and actions. The final draft must include enough information to restore or back out staged items later.

Execution checkpoints must summarize:

- Action mode or mixed actions.
- Item count and folder count.
- Total estimated size.
- Approved path prefixes.
- Extension counts and sizes.
- Largest items.
- Risk distribution.
- Recursive folders included.
- Symlinks found, skipped, or rejected.
- Cross-volume, cross-share, or network-share moves.
- Staging, archive, manifest, log, and script paths.
- Exact self-test, dry-run, and write commands.

## Backout And Restore

Preserve original paths so staged or compressed items can be reviewed, restored, or selectively backed out later.

For every staged, moved-to-system-trash, compressed, or deleted item, record:

- Run ID and item ID.
- Original full path.
- Current path: staged path, archive path, system-trash note, or deleted.
- Filename.
- Size before action and resulting size when available.
- Action taken and timestamp.
- Description and risk.
- Reversibility.
- Restore or backout instructions when possible.

For staged files, record enough information to generate a restore script later, including selective restore commands such as `restore 1.3`, `restore 2.1 2.4`, or `restore all`. If the original path now exists, do not overwrite it without explicit user approval.

For compressed files, record whether originals remain, were staged, were moved to the system trash, or were deleted. Restoration may mean extracting the archive or moving staged originals back.

For system-trash moves, record the original path and tell the user restoration may need the operating system's recovery UI.

For permanent deletion, mark restore as unavailable unless an archive, backup, or staged copy exists.

## Generated Cleanup Script

For more than one file, recursive folders, compression runs, or mixed-risk cleanup, generate a reviewable script rather than issuing inline delete commands. Place the script inside the run folder:

```text
CodexJanitor/<run-id>/cleanup.py
```

Start from `scripts/cleanup_template.py` when possible. Copy it into the run folder and adapt only the manifest schema or action handling needed for the specific cleanup. The template provides exact-path manifest loading, reversible move behavior where available, staging, permanent delete, JSONL logging, preflight checks, dry-run, and a self-test mode.

The script must be human-readable:

- Keep exact approved paths visible near the top or load them from `cleanup_manifest.json` while also showing them in `cleanup_plan.md`.
- Avoid encoded blobs, hidden path generation, broad globbing, or clever abstractions.
- Include comments for safety checks and action modes.
- Default to dry-run behavior.
- Support `--self-test`, `--dry-run`, `--execute`, and an explicit write mode such as `--stage`, `--trash`, `--compress`, or `--delete`. Write modes must dry-run unless `--execute` is passed.

Offer a review checkpoint after generating the script. Stop for human review unless the user explicitly says they do not want to review the script and wants Codex to proceed through self-test and dry-run. Even when review is skipped, still show the script path, exact item list, action mode, and commands before running write actions.

The safe execution sequence is:

1. Generate `cleanup_plan.md`, `cleanup_manifest.json`, `manifest.md`, and `cleanup.py` in `CodexJanitor/<run-id>/`.
2. Show the final draft summary, script path, exact item list, planned actions, and dry-run command.
3. Ask whether the user wants to review the script before any execution.
4. If the user skips review, run only `--self-test` and a mode-specific dry-run; do not run write actions yet.
5. Run `python cleanup.py --self-test`.
6. Run the mode-specific dry-run against real approved paths, such as `python cleanup.py --stage --dry-run`, `python cleanup.py --trash --dry-run`, or `python cleanup.py --delete --dry-run`.
7. Show dry-run output and ask for final confirmation.
8. Run the selected write action with `--execute` only after final confirmation.
9. Log each item outcome.

Self-test mode must create fake files and nested folders only inside:

```text
CodexJanitor/<run-id>/self-test/
```

Self-test must exercise the same code path as real cleanup and verify:

- Exact allowlisted fake files and recursive folders are handled.
- Nested files are staged, moved, deleted, or compressed as expected.
- Missing files are skipped safely.
- Logs are written.
- Dry-run changes nothing.
- Rejected paths are rejected.
- Symlinks are skipped or rejected.
- No path outside `self-test/` is touched.

Prefer staging behavior for self-tests. Do not send self-test files to the real system trash unless the user explicitly wants to test that integration, because that can leave fake entries in the user's recovery UI.

Measure-twice checks:

- Refuse to run if the approved item count differs from the manifest or expected count.
- Refuse to run if the total measured size differs materially from the precomputed size; ask the user before continuing.
- Refuse paths outside precomputed approved path prefixes.
- Refuse unexpected file extensions when an extension allowlist was established.
- Refuse empty paths, drive roots, home/profile roots, workspace roots, system roots, and broad parent directories.
- Refuse wildcard or glob-expanded targets; every real target must be an exact path from the approved allowlist.
- Refuse symlink traversal unless the user explicitly approved symlink handling.
- Refuse cross-volume, cross-share, or network-share moves unless the user explicitly confirmed that cost/risk.
- Capture drive free space before dry-run, before write, and after verification.
- Preflight approved targets for read-only attributes, access-control errors, protected child folders, active files, symlinks or special filesystem links, and unexpected child counts.
- Offer an optional reversible write-permission probe only after exact targets are approved: create a uniquely named zero-byte sentinel file inside the exact target directory, delete it, and log success/failure. Never run this during metadata-only scans.

Retry and reconciliation rules:

- If deletion partially succeeds, automatically rescan exact approved targets, report remaining size, update the cleanup log, and produce a follow-up plan for remnants.
- Offer safe retry modes only for exact approved targets, such as clearing read-only attributes and retrying removal. Keep retries opt-in or gated by final confirmation.
- Log retries separately from initial actions.
- Do not broaden paths during retry.

## Compression With Expiry

Offer compression when the user wants to reclaim space but is not ready to delete files. This is best for old text-heavy folders, logs, CSV/JSON/XML exports, project snapshots, documents, and collections of many small files.

Avoid compression when it is unlikely to help or likely to break app behavior:

- Already-compressed media such as most videos, photos, music, ZIP/7z/RAR archives, installers, disk images, and many PDFs.
- App-managed folders, databases, mail stores, browser profiles, photo libraries, cloud-sync folders, source repositories, package caches, build artifacts, VM/container data, and system files unless the user explicitly asks.
- Files that an app may currently be using.

Use `CodexJanitor/<run-id>/archives/` for archives created during a cleanup run. Keep an expiry ledger in the run manifest and cleanup log.

Compression approval must show:

- Exact filenames and full paths.
- Original total size and estimated or actual archive size.
- Estimated savings before compression, clearly labeled as an estimate.
- Archive path.
- Expiry review date.
- Whether originals will be kept, staged, moved to the system trash, or deleted after successful archive verification.

Prefer this safe sequence:

1. Estimate compression savings from file types and original sizes, but label the estimate as uncertain.
2. Create the archive.
3. Verify the archive can be listed or tested with the available archive tool.
4. Log original paths, archive path, original size, archive size, compression ratio, estimated savings, expiry date, and verification result.
5. Ask before staging, moving to the system trash, or deleting originals. If the user is unsure, keep originals.
6. After originals are staged, moved to the system trash, or deleted, log the actual space outcome: original size, archive size, real reclaimed space, and any temporary extra space used.

Space accounting rules:

- Before archive creation: report `estimated savings`.
- After archive verification while originals remain: report `archive size` and `potential savings`; do not claim reclaimed space.
- After originals are staged or removed: report `real reclaimed space = original size - archive size` when archive and originals are on the same volume.
- If originals are moved to staging on the same volume, the user has not reclaimed the full original size yet; report it as `reviewable/staged space`, not deleted space.
- If the archive is on a different volume, distinguish `local space freed` from `total storage consumed`.

Expiry rule: an expiry date is a future review trigger, not permission for automatic deletion. When Codex later finds expired archive/staging entries, it should list exact filenames, original paths, archive paths, sizes, and expiry dates, then ask for confirmation before deleting anything.

## Staging Folder

Offer staging as a safer alternative to deletion for any exact selected file or folder. Strongly recommend staging for personal files, old downloads, archives, duplicate-looking files, old scripts, PDFs/text files, media, and other ambiguous user-created data.

Before deleting or moving selected items to the system trash, ask whether the user wants staging first. For generated files, caches, and build artifacts, staging is still available but usually less useful than deletion/regeneration or official cleanup commands.

Use this default staging layout:

```text
CodexJanitor/<run-id>/
```

Choose a run ID that is unique and human-readable, such as `2026-04-24-1930` or `2026-04-24-downloads-review`. Ask for the parent location if the cleanup is broad; otherwise place it in the current workspace for project-local cleanup or in the user's home/profile folder for personal cleanup.

Inside the run folder, create:

```text
cleanup_plan.md
cleanup.py
cleanup_manifest.json
manifest.md
items/
archives/
self-test/
```

Move staged files under `items/`. Preserve original context by either recreating the original folder structure under `items/` or using collision-safe names. Record the original path and staged path in `manifest.md`.

Staging rules:

- Prefer staging on the same drive/volume as the original files; same-volume moves are usually fast and do not require duplicate free space.
- Warn before cross-drive, cross-share, or network-share staging because it may copy data, take time, and temporarily require extra space.
- Warn or discourage staging when it affects cloud-sync folders, app-managed data, package caches, build artifacts, VM/container data, system files, app profiles, mail stores, photo libraries, databases, or other data where moving files can break an app or service.
- Do not stage risky managed data unless the user explicitly confirms the exact paths after the warning.
- Do not stage files that an app may currently be using; ask the user to close the app first or skip them.
- Treat staging as a write action: require exact item confirmation and log every move.

## Cleanup Log

Create or update a cleanup log whenever the user approves deletion, system-trash moves, cache pruning, uninstall guidance that Codex executes, or any other write cleanup action. Do not log routine read-only scans unless the user asks.

Prefer writing the log inside the current workspace when the cleanup is project-local. For broader computer cleanup, ask where the user wants the log saved; if they do not care, use a clearly named Markdown file such as `disk-cleanup-log-YYYY-MM-DD.md` in the current working directory.

Each log entry must include:

- Timestamp.
- Run ID and item ID.
- Action type: moved to system trash, staged, compressed, deleted, cache-clean command, app cleanup, skipped, or failed.
- Exact original path, staged path, archive path, or command.
- Estimated size before cleanup.
- Resulting size when available.
- Estimated savings and actual reclaimed space when compression is involved.
- Initial dry-run size, actually removed size, remaining size, skipped archive/staging items, partial failures, retry actions, and final verification result when applicable.
- Drive free space before dry-run, before write, and after verification when available.
- Short description of what the item was.
- Risk label and reason.
- Reversibility: reversible, partially reversible, or permanent.
- Expiry review date when applicable.
- Outcome and any error message.

Use this Markdown table shape:

```markdown
| Time | Action | Target | Size Before | Size After | Description | Risk | Reversibility | Expiry | Outcome |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
```

After cleanup, summarize total estimated reclaimed space and point to the log path.

## Hard Stops

Stop and ask before any action that would:

- Permanently delete data.
- Empty the system trash.
- Remove application support/config directories.
- Delete cloud-sync folders or backup directories.
- Clean package-manager stores, Docker data, VM images, mail stores, photo libraries, or development worktrees.
- Inspect contents of personal files or media beyond the user's approved scope.
- Require administrator privileges.

If the user insists on deletion, make it a separate explicit step after the report.
