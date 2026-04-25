# Disk Space Janitor Skill

A Codex skill for safely finding disk-space cleanup opportunities.

The skill focuses on identification, triage, review, and auditable cleanup planning. It does not encourage blind deletion. The default flow is to find cleanup candidates, explain the tradeoffs, and ask the user before any write action.

## What It Does

- Finds large files, stale downloads, caches, build artifacts, and other likely cleanup opportunities.
- Starts with metadata before inspecting file contents.
- Labels cleanup candidates by risk.
- Offers review, staging, compression, or deletion planning depending on what the user wants.
- Keeps cleanup decisions explicit and auditable.

## Use With Codex

In a Codex environment where the skill is available, invoke it with:

```text
Use $disk-space-janitor to inspect this workspace for cleanup opportunities. Do not delete anything.
```

For team distribution, package this workflow as a Codex plugin that includes the skill.

## Safety Model

The skill is intentionally conservative:

- Metadata scan first.
- Content inspection only after approval.
- Exact filenames and full paths before cleanup.
- Interactive cleanup draft before execution.
- Reversible options are preferred before permanent deletion.
- Final write actions require confirmation.
- Logs preserve cleanup decisions for review.

## Example Workflow

```text
User: Use $disk-space-janitor to inspect my Downloads folder. Do not delete anything.

Codex: I will start with a read-only metadata scan. Disk cleanup can cause data loss, so I will not inspect file contents or modify anything without your approval.

Codex: Scan complete. I found about 42.8 GB of cleanup candidates:
- 18.4 GB in old installers under /Downloads/installers
- 9.7 GB in archived project exports under /Downloads/exports
- 6.2 GB in cache-like folders under /Downloads/app-cache
- 5.1 GB in duplicate-looking media exports under /Downloads/media-review
- 3.4 GB in PDFs and text files that need review before any recommendation

User: Inspect the PDFs and text files, but leave media alone.

Codex: After content-aware review, I recommend:
- Low risk: 6.2 GB app-cache folder, likely disposable
- Medium risk: 18.4 GB old installers, good staging candidates
- Medium risk: 9.7 GB archived exports, good compression candidates
- High risk: 3.4 GB PDFs and text files, keep or review manually
- Not reviewed: 5.1 GB media exports

User: Delete the 6.2 GB app-cache folder. Do not touch anything else.

Codex: Final draft:
- Delete /Downloads/app-cache, estimated 6.2 GB
- Leave installers, exports, PDFs, text files, and media unchanged
- Generate a cleanup script with exact-path checks, item counts, size checks, and a dry-run first

Codex: Dry-run complete. The script matched 1 approved folder under the allowed path, measured 6.2 GB, and found no unexpected paths.

User: Approved. Run the delete.

Codex: Delete complete. The script removed only the approved app-cache folder and verified the folder is gone.
Codex: I recorded the reclaimed size and wrote the cleanup log in CodexJanitor/2026-04-24-downloads-review/.
```

## Privacy

The skill defaults to a high-sensitivity privacy posture. It should not infer whether a machine is personal, work, school, shared, or managed from installed apps, games, filenames, folder names, browser profiles, or media. If that context would materially improve safety or recommendations, Codex should ask the user directly and use the answer only to adjust caution.

## Disclaimer

This skill is provided as-is, without warranty. Disk cleanup can cause data loss if used incorrectly. Users are responsible for reviewing all proposed actions, maintaining backups, and deciding whether to execute any staging, deletion, compression, or other cleanup operation. This project is designed to reduce risk through scoped scans, dry-runs, confirmations, and logs, but it cannot guarantee that any file is safe to remove.
