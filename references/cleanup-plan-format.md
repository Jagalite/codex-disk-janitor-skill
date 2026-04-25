# Cleanup Plan Format

Cleanup plans must be easy to review and revise. Use stable IDs and exact paths before any write action.

## Candidate Table

Use a concise table for findings:

| ID | Path | Type | Size | Risk | Reason | Suggested next step |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | `/Downloads/app-cache` | directory | 6.2 GB | Low | Cache-like folder; can likely be regenerated | Review exact path, then dry-run deletion if approved |
| 1.2 | `/Downloads/archive-export.zip` | archive | 4.8 GB | Medium | Old export; may contain user data | Review or keep |
| 1.3 | `/Downloads/tax-records.pdf` | document | 120 MB | High | Personal document category | Keep/manual review |

## Cleanup Draft Table

Before any write action, produce a final draft:

| ID | Path | Type | Size | Risk | Proposed action | Reason | Reversible? | Requires content review? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.1 | `/Downloads/app-cache` | directory | 6.2 GB | Low | Move to system trash after dry-run | Approved cache-like folder | Usually, until trash is emptied | No |

## Approval Block

Use a short approval block. The user should be able to approve, remove, or revise each action.

```markdown
Approved actions:
- [ ] Delete 1.1 `/Downloads/app-cache`
- [ ] Stage 2.3 `/Projects/old-build-output`

Not touched:
- 1.2 `/Downloads/archive-export.zip`
- 1.3 `/Downloads/tax-records.pdf`
- 3.1 `/Photos/library`

Dry-run result:
- expected paths matched
- estimated bytes: 6.2 GB
- unexpected paths found: none
```

## JSON Plan Validation

When a cleanup plan is represented as JSON, validate it with `scripts/validate_cleanup_plan.py` before any execution step. The validator is read-only and should:

- Reject empty paths.
- Reject roots and broad parent paths.
- Reject path traversal outside approved scope.
- Reject symlinks unless explicitly allowed.
- Reject mount points unless explicitly allowed.
- Verify each path still exists.
- Verify the current type matches the expected type.
- Estimate current size.
- Report unexpected expansion.
- Output a dry-run summary.

Validation is not approval to execute. It only checks whether the final plan still matches the approved exact paths.

## Required Notes

Every cleanup draft should include:

- Scope scanned.
- Whether the scan was complete or partial.
- Exact paths.
- Proposed action per path.
- Estimated reclaimed size.
- Risk label and reason.
- What will be left unchanged.
- Dry-run command or procedure.
- Reversibility or rollback notes.
- Audit log destination if applicable.

Do not ask for final approval from group summaries alone.
