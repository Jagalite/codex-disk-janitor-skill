# Example: Downloads Review

This example shows a conservative review of a Downloads folder. The data is fake.

## Request

```text
User: Use $disk-space-janitor to review my Downloads folder. Start read-only and do not delete anything.
```

## Metadata Summary

```text
Codex: I will scan metadata first. I will not inspect contents or modify files without approval.
```

| ID | Path | Type | Size | Risk | Reason | Suggested next step |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | `/Downloads/installers/` | directory | 14.8 GB | Medium | Old installers may be removable, but may be needed for reinstall/offline use | Review exact items |
| 1.2 | `/Downloads/project-exports/` | directory | 9.6 GB | Medium | Archives/exports may contain user-created data | Review or archive |
| 1.3 | `/Downloads/manuals-and-pdfs/` | directory | 3.2 GB | High | PDFs may include personal, legal, financial, work, or identity files | Manual review/content review only if approved |
| 1.4 | `/Downloads/media/` | directory | 7.9 GB | High | Photos, videos, and audio are user data | Keep/manual review |
| 1.5 | `/Downloads/app-cache/` | directory | 4.4 GB | Low | Cache-like folder; likely regenerated | Candidate for cleanup draft after approval |

## Optional Content Review

```text
User: Inspect the PDFs by filename and headings only. Do not inspect media.
```

| ID | Path | Size | Risk | Result |
| --- | --- | --- | --- | --- |
| 1.3 | `/Downloads/manuals-and-pdfs/` | 3.2 GB | High | Contains mixed manuals and personal-looking records. Keep/manual review. |
| 1.4 | `/Downloads/media/` | 7.9 GB | High | Not inspected. Keep/manual review. |

## Cleanup Draft

```text
User: Prepare a draft to delete only the app-cache folder.
```

| ID | Path | Type | Size | Risk | Proposed action | Reason | Reversible? | Requires content review? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.5 | `/Downloads/app-cache/` | directory | 4.4 GB | Low | Delete after dry-run | User selected exact cache-like folder | No, unless staged/trash first | No |

Approved actions:

- [ ] Delete 1.5 `/Downloads/app-cache/`

Not touched:

- 1.1 `/Downloads/installers/`
- 1.2 `/Downloads/project-exports/`
- 1.3 `/Downloads/manuals-and-pdfs/`
- 1.4 `/Downloads/media/`

Dry-run result:

- expected paths matched
- estimated bytes: 4.4 GB
- unexpected paths found: none
