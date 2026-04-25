# Safety Model

Disk Space Janitor is designed for cautious disk cleanup. The goal is to help the user understand what is taking space and decide what to do, not to automate aggressive deletion.

## Read-Only First

Start with read-only inspection. A request to "clean up" or "free space" should be interpreted as permission to investigate and plan, not permission to delete.

Read-only work may include:

- Checking disk usage.
- Listing file and directory metadata.
- Measuring sizes.
- Grouping candidates by category.
- Reporting partial scan limits.

## Metadata Before Content

Use metadata before opening file contents. Metadata includes path, type, size, modified time, access time if available, item counts, and apparent category.

Content inspection can reveal sensitive data. Ask before opening documents, PDFs, source files, logs, exports, images, audio, video, archives, databases, or app state.

## Explicit Consent

Require explicit consent for each escalation:

- Broader scan scope.
- Content inspection.
- Staging or moving files.
- Compression.
- System trash moves.
- Permanent deletion.
- Administrator or elevated access.

Do not assume consent from prior unrelated approval.

## Dry-Runs

Before any write action, run or present a dry-run. A dry-run should verify:

- Approved scope.
- Exact paths.
- Item count.
- Estimated size.
- Path prefixes.
- Link/mount handling.
- Unexpected path expansion.

If the dry-run output differs from the cleanup draft, stop and ask.

## Exact Path Checks

Every write action must operate on exact approved paths. Avoid broad globs, generated parent paths, recursive force operations on computed paths, or implicit expansion.

Reject empty paths, drive roots, home/profile roots, workspace roots, system roots, and broad parent directories unless the user has explicitly approved a narrowly defined operation and the risk is explained.

## Audit Logs

Write or present an audit log for approved write actions. The log should include:

- Timestamp.
- Approved item ID.
- Original path.
- Action taken.
- Size before action.
- Resulting size when available.
- Risk label.
- Outcome.
- Error or skipped reason.
- Reversibility notes.

## Reversible Options First

Prefer least-destructive options:

1. Keep.
2. Review manually.
3. Use app-native cleanup.
4. Stage/quarantine.
5. Move to system trash.
6. Compress only when preservation makes sense.
7. Permanently delete only after explicit final approval.

## Least-Destructive Cleanup

When multiple paths reclaim similar space, prefer the path with lower risk and easier recovery. Generated caches and build outputs are usually better candidates than user-created documents, media, backups, databases, or app state.

No file is guaranteed safe to remove. Risk labels are decision aids, not guarantees.
