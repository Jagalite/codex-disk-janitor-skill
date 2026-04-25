# Risk Taxonomy

Use risk labels to make cleanup decisions reviewable. Risk labels do not authorize deletion by themselves.

## Low Risk

Usually generated, cache-like, temporary, or easy to recreate. Still show findings and ask before write actions.

Examples:

- Build output directories such as `target/`, `dist/`, `build/`, `.next/`, and coverage output.
- Generated caches.
- Package manager caches cleaned through official commands.
- Temp folders.
- Logs after review.
- Clearly disposable test output.

Low risk does not mean safe in every context. A build folder can still contain local artifacts a user wants to keep.

## Medium Risk

Often removable after review, but deletion may cost time, bandwidth, local history, or recovery effort.

Examples:

- Old installers.
- Archives.
- Duplicate-looking exports.
- Old downloads.
- Regenerated dependencies such as `node_modules/` or `.venv/`.
- Large logs with possible debugging value.
- Tool caches that may need re-downloads.

Medium risk items should be expanded to exact paths before any cleanup draft.

## High Risk

User data, app state, synced data, backups, or data with meaningful loss potential. Default to keep/manual review.

Examples:

- Documents.
- Photos, videos, audio, and media libraries.
- Source repositories.
- Databases.
- VM images.
- Cloud-sync folders.
- Backups.
- Config/state files.
- Mail, messages, browser profiles, notes, password stores, and app support data.
- Financial, legal, tax, identity, medical, school, or work files.

High risk items should not be proposed for deletion unless the user specifically selects them and approves the final cleanup draft.

## Unknown

Anything with unclear purpose, unclear ownership, insufficient metadata, inaccessible contents, or ambiguous context.

Examples:

- Unrecognized large folders.
- Extensionless large files.
- App directories with unclear state.
- Files in unfamiliar project or sync locations.
- Items from partial scans.

Unknown defaults to keep/manual review.
