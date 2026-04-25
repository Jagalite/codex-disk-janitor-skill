# Example: Docker Cache Review

This example shows Docker cleanup planning. The data is fake.

## Request

```text
User: Use $disk-space-janitor to review Docker disk usage. Do not delete anything yet.
```

## Metadata Summary

| ID | Path | Type | Size | Risk | Reason | Suggested next step |
| --- | --- | --- | --- | --- | --- | --- |
| 1.1 | Docker build cache | Docker cache | 18.6 GB | Low | Build cache is usually regenerable | Use Docker-native cleanup after dry-run/listing |
| 1.2 | Unused images | Docker images | 11.3 GB | Medium | Images can be pulled/rebuilt, but may cost time/bandwidth | Review image list |
| 1.3 | Stopped containers | Docker containers | 2.4 GB | Medium | May contain logs or debugging state | Review container names |
| 1.4 | `postgres-data` | Docker volume | 21.7 GB | High | Volume may contain database state | Keep/manual review |
| 1.5 | `/home/user/project/uploads` | bind mount | 8.2 GB | High | Bind-mounted user data visible to containers | Keep/manual review |

## Recommendation

```text
Codex: Docker build cache is the lowest-risk cleanup candidate in this report. Volumes and bind mounts are high risk and should not be deleted unless you explicitly approve exact targets after review.
```

## Cleanup Draft

| ID | Path | Type | Size | Risk | Proposed action | Reason | Reversible? | Requires content review? |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 1.1 | Docker build cache | Docker cache | 18.6 GB | Low | Prune after dry-run/listing | Regenerable cache | No | No |

Approved actions:

- [ ] Prune 1.1 Docker build cache only

Not touched:

- 1.2 Unused images
- 1.3 Stopped containers
- 1.4 `postgres-data` volume
- 1.5 `/home/user/project/uploads` bind mount

Dry-run result:

- expected cleanup target matched
- estimated bytes: 18.6 GB
- unexpected paths found: none

## Docker Safety Notes

- Distinguish image/container/build-cache cleanup from volumes and bind-mounted user data.
- Never delete bind mount contents just because they are visible in a container.
- Treat volumes as high risk unless the user explicitly approves exact volume cleanup.
