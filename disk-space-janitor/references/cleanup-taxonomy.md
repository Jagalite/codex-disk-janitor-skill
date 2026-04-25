# Cleanup Taxonomy

Use this reference to classify disk-space candidates and choose cleanup advice.

## Risk Labels

`low`: Usually regenerated or clearly disposable. Still present findings first and let the user choose.

Examples:
- OS temp folders.
- App caches.
- Browser caches through browser settings.
- Old installers in Downloads.
- Build outputs such as `node_modules`, `target`, `dist`, `.next`, `.turbo`, `coverage`, `.pytest_cache`.
- Package-manager caches when cleaned through their official command.

`medium`: Often safe, but may cost time, bandwidth, settings, or local history.

Examples:
- Docker images/volumes.
- VM images and simulator runtimes.
- Old logs and crash dumps.
- Duplicate-looking archives.
- Local package stores.
- Old device backups.
- Large media already backed up elsewhere.

`high`: User data or data with unclear ownership. Do not recommend deletion without careful review.

Examples:
- Documents, PDFs, notes, photos, videos, music, audio recordings, mail stores, source repositories.
- Cloud-sync folders.
- Password manager, browser profile, chat app, notes app, or database folders.
- Anything under system directories unless using OS-native cleanup UI.

## Common Candidate Classes

Downloads:
- Look for old installers, disk images, ZIP files, duplicate downloads, and large media.
- Recommend sorting by size and last modified time. Ask the user to review personal files.

Caches and temp files:
- Prefer app or OS cleanup UIs.
- Safe candidates are usually inside Temp, cache, crash dump, or build cache directories.
- Do not delete active app databases, profiles, or support folders just because they are large.

Development artifacts:
- `node_modules`, Rust `target`, Python `.venv`, Java/Gradle caches, build folders, coverage folders, and generated bundles can be large.
- Confirm whether the project is active. Recommend project-specific cleanup commands when available.
- Source scripts and notebooks are user-created code; treat them as high risk unless clearly generated, vendored, or disposable.

Text files and PDFs:
- Start with path, size, extension, modified time, and folder context.
- Ask before opening contents to rank importance.
- Treat legal, financial, medical, identity, work, school, tax, contract, invoice, resume, and personal-note documents as high risk.
- Machine-generated reports, exported logs, readmes from installers, and duplicate downloaded manuals may be medium or low risk after inspection.
- Compression can help for text-heavy files and folders, but many PDFs are already compressed; verify actual savings before deleting originals.

Scripts and source files:
- Treat files in active source repositories as high risk by default.
- Generated code, dependency directories, compiled outputs, lockfile-adjacent caches, and coverage reports can be lower risk.
- Old one-off scripts are `review first`, not `safe to delete`; they may encode personal automation or credentials.
- Do not quote secrets, tokens, keys, or private endpoints found during inspection.

Containers and virtual machines:
- Docker and VM data can reclaim a lot of space but often includes important local state.
- Report sizes and ask before pruning images, volumes, or VM disks.
- Prefer Docker/VM/native cleanup tools over filesystem deletion.

Windows app-managed locations:
- Treat Program Files, ProgramData, game launchers, Docker, WSL, BlueStacks, Android emulators, VM folders, and installed app directories as app-managed.
- Look for uninstallers, app-native cleanup, launcher cleanup, or official commands before recommending direct filesystem deletion.
- Direct deletion may leave registry entries, broken services, shortcuts, update records, and uninstall records.
- If direct deletion is requested, require exact paths, app-closed confirmation, preflight checks, and final confirmation.

Backups and sync:
- Device backups, Time Machine snapshots, Windows restore data, and cloud-sync folders need extra care.
- Prefer the vendor UI. Do not remove backup sets manually.

Media libraries:
- Photos, videos, music, and game recordings are user data.
- Suggest archiving, moving to external storage, or deduplicating with a specialized tool.
- For images, use vision only after user approval when importance depends on content.
- For videos, inspect metadata and representative frames when tools are available.
- For audio, use metadata and transcription when available; otherwise avoid content claims.
- Compression usually does not reclaim much space for already-compressed media; prefer review, staging, external storage, or deduplication.

Content-aware review:
- Use it only as a second stage after a metadata report.
- Inspect only the files or folders the user selected.
- Summarize importance signals rather than exposing sensitive contents.
- Classify personal or ambiguous content as high risk even if it is old or large.

Compression and expiry:
- Use compression as a preservation option, not as proof that originals can be deleted.
- Good candidates include old text-heavy folders, logs, CSV/JSON/XML exports, project snapshots, and many-small-file document collections.
- Bad candidates include app-managed data, databases, cloud-sync folders, source repositories, package caches, build artifacts, media libraries, archives, installers, VM/container data, and system files unless explicitly requested.
- Expiry dates create a later review queue. Do not delete expired originals or archives without showing exact paths and getting fresh confirmation.

## OS Hints

Windows:
- Low-risk starting points: Settings > System > Storage, Disk Cleanup, Storage Sense, `%TEMP%`, `%LOCALAPPDATA%\Temp`, `%LOCALAPPDATA%\CrashDumps`, Downloads.
- High-risk areas: `C:\Windows`, `C:\Program Files`, application data, user profile databases, cloud-sync roots.
- Recycle Bin can be large, but emptying it is destructive from the user's perspective; ask first.

macOS:
- Low-risk starting points: System Settings > General > Storage, Trash review, `~/Downloads`, `~/Library/Caches`.
- Medium-risk areas: Xcode DerivedData, iOS device backups, Docker data, simulator runtimes.
- High-risk areas: Photos libraries, Mail, Messages, `~/Library/Application Support`.

Linux:
- Low-risk starting points: `~/.cache`, package-manager caches via official commands, old downloads, build outputs.
- Medium-risk areas: Docker, Flatpak/Snap caches, journal logs, VM images.
- High-risk areas: `/etc`, `/var/lib`, home data directories, database directories.

## Recommendation Style

Use concrete language:
- "Likely safe to remove after closing the app."
- "Use the app's cleanup UI rather than deleting this folder manually."
- "Review before deleting; this looks like user-created data."
- "Can be regenerated, but deletion may require reinstalling dependencies."

Avoid overpromising:
- Do not say an item is safe only because it is old or large.
- Do not assume duplicate filenames are duplicate content.
- Do not claim cloud files are backed up unless verified.
- Do not claim a scan is complete when caps, access-denied paths, skipped reparse points, or known-location limits were reached.
