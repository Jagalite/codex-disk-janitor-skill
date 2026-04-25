# Disk Space Janitor

Disk Space Janitor is a conservative Codex skill for auditing disk usage, identifying cleanup candidates, and producing reviewable cleanup plans before any write action.

It exists because disk cleanup is easy to get wrong. Large files are not automatically disposable, old files are not automatically unimportant, and app data can be fragile. This skill helps Codex slow down, inspect metadata first, classify risk, and ask for explicit approval before changing anything.

## What It Does

- Audits disk usage in a user-approved scope.
- Starts with metadata such as path, size, type, and modified time.
- Groups likely cleanup candidates by risk.
- Asks before inspecting file contents.
- Produces reviewable cleanup drafts with exact paths.
- Uses dry-runs before any approved write action.
- Records what happened for auditability.

## What It Will Not Do

- It will not delete, move, compress, truncate, rewrite, or modify files by default.
- It will not inspect file contents without approval.
- It will not treat old or large files as safe to remove on that basis alone.
- It will not follow links, mounted paths, cloud-sync folders, Docker mounts, or app-managed storage casually.
- It will not hide destructive actions inside prose.

## Use With Codex

In a Codex environment where the skill is available, invoke it with:

```text
Use $disk-space-janitor to inspect this workspace for cleanup opportunities. Do not delete anything.
```

For broader cleanup, name the scope explicitly:

```text
Use $disk-space-janitor to review my Downloads folder. Start read-only and ask before inspecting file contents.
```

For team distribution, package this repository as a Codex plugin or include the root `SKILL.md` and supporting `docs/` and `examples/` files in the plugin bundle.

## Safety Guarantees

The skill is designed around these guardrails:

- Read-only inspection is the default.
- Metadata comes before content inspection.
- Content review requires user approval.
- Cleanup candidates are risk-classified.
- Exact paths are shown before write actions.
- Cleanup drafts are explicit and editable.
- Dry-runs happen before execution.
- Reversible options are preferred over permanent deletion.
- Final write actions require explicit approval.
- Results are verified and logged or presented for review.

These guardrails reduce risk, but they do not guarantee that any file is safe to remove.

## Example Usage

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
- Medium risk: 18.4 GB old installers, review before deletion
- Medium risk: 9.7 GB archived exports, review or archive
- High risk: 3.4 GB PDFs and text files, keep or review manually
- Not reviewed: 5.1 GB media exports

User: Delete the 6.2 GB app-cache folder. Do not touch anything else.

Codex: Final cleanup draft:
- Delete /Downloads/app-cache, estimated 6.2 GB
- Leave installers, exports, PDFs, text files, and media unchanged
- Run a dry-run with exact-path, item-count, and size checks before execution

Codex: Dry-run complete. The script matched 1 approved folder under the allowed path, measured 6.2 GB, and found no unexpected paths.

User: Approved. Run the delete.

Codex: Delete complete. The approved app-cache folder was removed and the result was verified.
Codex: I recorded the reclaimed size and wrote the cleanup log in CodexJanitor/2026-04-24-downloads-review/.
```

## Repo Layout

```text
.
|-- README.md
|-- SKILL.md
|-- LICENSE
|-- examples/
|   |-- downloads-review.md
|   |-- workspace-review.md
|   `-- docker-cache-review.md
`-- docs/
    |-- safety-model.md
    |-- risk-taxonomy.md
    |-- cleanup-plan-format.md
    `-- os-notes.md
```

## Documentation

- `SKILL.md`: agent-facing instructions for Codex.
- `docs/safety-model.md`: safety philosophy and consent model.
- `docs/risk-taxonomy.md`: risk levels and examples.
- `docs/cleanup-plan-format.md`: expected cleanup draft format.
- `docs/os-notes.md`: platform-specific cautions.
- `examples/`: realistic safe workflows.

## Disclaimer

This skill is provided as-is, without warranty. Disk cleanup can cause data loss if used incorrectly. Users are responsible for reviewing all proposed actions, maintaining backups, and deciding whether to execute any staging, deletion, compression, or other cleanup operation. This project is designed to reduce risk through scoped scans, dry-runs, confirmations, and logs, but it cannot guarantee that any file is safe to remove.
