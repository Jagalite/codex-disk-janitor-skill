# Example: Workspace Review

This example shows a developer workspace scan. The data is fake.

## Request

```text
User: Use $disk-space-janitor to inspect this development workspace. Do not delete anything.
```

## Metadata Summary

| ID | Path | Type | Size | Risk | Reason | Suggested next step |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | `/workspace/app/target/` | directory | 12.4 GB | Low | Rust build output, usually regenerated | Candidate after project confirmation |
| 1.2 | `/workspace/web/node_modules/` | directory | 3.8 GB | Medium | Regenerated dependency directory, but reinstall may take time | Candidate after confirmation |
| 1.3 | `/workspace/web/.next/` | directory | 1.6 GB | Low | Generated framework output | Candidate after confirmation |
| 1.4 | `/workspace/api/dist/` | directory | 890 MB | Low | Build output | Candidate after confirmation |
| 1.5 | `/workspace/tools/.venv/` | directory | 2.1 GB | Medium | Regenerable environment, but may contain local tool state | Review first |
| 1.6 | `/workspace/app/.git/` | directory | 620 MB | High | Repository history and state | Keep |
| 1.7 | `/workspace/app/.env` | file | 2 KB | High | May contain credentials | Keep; do not inspect unless approved |
| 1.8 | `/workspace/data/dev.db` | file | 4.2 GB | High | Database | Keep/manual review |

## Recommendation

```text
Codex: The lowest-risk candidates are generated build outputs. I will preserve source, .git, .env, databases, and project state.
```

## Cleanup Draft

| ID | Path | Type | Size | Risk | Proposed action | Reason | Reversible? | Requires content review? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.1 | `/workspace/app/target/` | directory | 12.4 GB | Low | Move to system trash after dry-run | Build output | Usually, until trash is emptied | No |
| 1.3 | `/workspace/web/.next/` | directory | 1.6 GB | Low | Move to system trash after dry-run | Generated framework output | Usually, until trash is emptied | No |
| 1.4 | `/workspace/api/dist/` | directory | 890 MB | Low | Move to system trash after dry-run | Build output | Usually, until trash is emptied | No |

Approved actions:

- [ ] Move 1.1 `/workspace/app/target/` to system trash
- [ ] Move 1.3 `/workspace/web/.next/` to system trash
- [ ] Move 1.4 `/workspace/api/dist/` to system trash

Not touched:

- `/workspace/web/node_modules/`
- `/workspace/tools/.venv/`
- `/workspace/app/.git/`
- `/workspace/app/.env`
- `/workspace/data/dev.db`

Dry-run result:

- expected paths matched
- estimated bytes: 14.9 GB
- unexpected paths found: none
