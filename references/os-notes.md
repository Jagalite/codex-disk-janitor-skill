# OS Notes

These notes highlight common platform-specific risks. They are cautions, not deletion instructions.

## macOS

- `~/Library` can contain important app state.
- `~/Library/Application Support`, Mail, Messages, Photos libraries, and browser profiles are high risk.
- iCloud Drive sync can propagate deletion to remote copies and other devices.
- `.Trash` behavior depends on volume and user context.
- Xcode DerivedData and simulator data can be large, but prefer Xcode or platform-native cleanup when possible.

## Windows

- `AppData` can contain important app state, profiles, databases, and credentials.
- OneDrive sync can propagate deletion to remote copies and other devices.
- Junctions and reparse points can lead outside the apparent folder.
- Recycle Bin moves are more reversible than permanent deletion, but emptying the Recycle Bin is destructive from the user's perspective.
- Prefer Settings, Storage Sense, Disk Cleanup, uninstallers, and app-native cleanup for app-managed data.

## Linux

- Dot-directories such as `~/.config`, `~/.local`, and `~/.cache` can contain important config, state, and cache data.
- Package manager caches differ by distro; prefer official package manager cleanup commands.
- `/mnt`, `/media`, and `/run/media` may contain mounted volumes.
- Docker volumes and bind mounts need caution.
- System paths such as `/etc`, `/var/lib`, and database directories are high risk.

## WSL

- Deleting across `/mnt/c` can affect Windows files.
- Linux paths may map to Windows storage.
- Treat cross-boundary cleanup as higher risk and confirm exact paths.

## Docker

- Distinguish Docker image/container/build-cache cleanup from volumes and bind-mounted user data.
- Never delete bind mount contents just because they are visible in a container.
- Volumes may contain databases, uploads, caches, or local development state.
- Prefer Docker-native reporting and cleanup commands for images and build cache, with a dry-run or explicit list when available.
