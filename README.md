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

## Privacy

The skill defaults to a high-sensitivity privacy posture. It should not infer whether a machine is personal, work, school, shared, or managed from installed apps, games, filenames, folder names, browser profiles, or media. If that context would materially improve safety or recommendations, Codex should ask the user directly and use the answer only to adjust caution.

## Disclaimer

This skill is provided as-is, without warranty. Disk cleanup can cause data loss if used incorrectly. Users are responsible for reviewing all proposed actions, maintaining backups, and deciding whether to execute any staging, deletion, compression, or other cleanup operation. This project is designed to reduce risk through scoped scans, dry-runs, confirmations, and logs, but it cannot guarantee that any file is safe to remove.
