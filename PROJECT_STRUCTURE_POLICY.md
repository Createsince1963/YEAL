# Yeal Project Monitoring and Structure Policy

## Purpose and authority

This repository-specific policy adapts the owner's project-monitoring rules to Yeal. It is mandatory reading together with `CLAUDE.md` before structural cleanup, release work, or any task that can materially increase the repository.

The owner decides whether data may be deleted, moved, archived, migrated, committed, tagged, pushed, or removed from Git history. An AI agent may inspect and report without additional permission. It may change only what the owner's current request clearly authorizes. Unknown, active, productive, historical, or non-reproducible data must remain untouched until separately approved.

## Start-of-session check

Before changing files, record at least:

- active branch and current commit;
- `git status`, including untracked and modified tracked files;
- running Yeal builds/tests/apps when they can be detected read-only;
- new or unexpectedly large top-level paths;
- evidence that another session is editing the same worktree.

Never overwrite, reset, stash, delete, or include another session's changes in a commit. Report the overlap and work around it.

## Yeal's canonical structure

| Category | Canonical path | Rule |
|---|---|---|
| Application source | `BIN/versions/v0.1/PyModul/` | Tracked; this is the live source despite the historical path name. |
| Tests | `tests/` | Tracked; run Qt test files separately. |
| Documentation | `docs/`, `help/`, root Markdown files | Tracked; large media needs a documented reason. |
| CI | `.github/workflows/`, `ci/` | Tracked; generated APKs do not belong here. |
| Windows build work | `build/`, `build-next/` | Reproducible and ignored; remove only after checking that no build uses it. |
| Windows portable output | `dist/` | Ignored local output. `dist/Yeal.exe` requires the adjacent `dist/bin/`. |
| Staged/rollback output | `dist-next/`, `dist-old/` | Ignored and temporary; never leave both after a verified activation. |
| Test/QA scratch | `.test-tmp/` | Ignored, isolated and reproducible; tests must not share active scratch paths. |
| Cloud APK download | `BIN/versions/latest-cloud-build/` | Ignored local artifact; keep one named result, not duplicate aliases. |
| Historical source snapshots | `_snapshots/` | Treat as owner-controlled history, even when untracked. Do not delete automatically. |
| Pending deletion | `_to_delete/` | A review queue, not permission to delete. Inventory and request explicit approval. |
| User runtime data | `%LOCALAPPDATA%/Yeal` or `YEAL_DATA_DIR` | Must remain outside the repository. Never inspect or migrate without a direct request. |
| External tools | `../Tools_Central/` | External dependency source; never copy the complete tool tree into this repo. |

Node and FFmpeg are intentional release dependencies. The portable Windows output contains only `node.exe` and `ffmpeg.exe` in `dist/bin`, not their complete installations. Large release binaries should ultimately be distributed through a GitHub Release or another owner-approved artifact store, not committed to Git.

## Measurement and warning thresholds

Run a structure review before releases, after build/QA changes, after migrations, and whenever size or file count rises unexpectedly. Record the date, commit, total bytes, file count, directory count, top-level sizes, largest files, maximum depth, long paths, and new archives/databases/binaries.

Warn and stop for review when any of these occurs:

- a new directory exceeds 100 MB;
- a new file exceeds 50 MB;
- total size grows by more than 10 percent from the last recorded baseline;
- file or directory count grows by more than 20 percent;
- build/cache/temp data remains active without a cleanup path;
- a full project copy, archive, executable, APK, database, or runtime data appears in the source tree;
- multiple executable versions have no documented release purpose;
- a large binary enters reachable Git history.

A warning authorizes analysis only, never deletion.

## Required classification

Classify every material area as source, tests, documentation, knowledge/reviews, runtime data, database, cache, temporary data, build intermediate, application output, installer/portable package, archive/backup, Git data, logs/reports, screenshots/media, or unknown.

For each material area report its path, size, file count, purpose, producer, consumer, reproducibility, intended destination, deletion/move risk, rollback, and required owner approval.

## Cleanup tiers

1. **Reproducible and low risk:** inactive build intermediates, caches, isolated test scratch, duplicate generated aliases verified by hashes.
2. **Review or backup required:** old binaries, APKs, screenshots, media, archives, `_snapshots/`, `_to_delete/`, and unknown old files.
3. **Migration and acceptance required:** databases, user data, histories, authentication material, download libraries, and any path change read by the application.
4. **Owner strategy required:** retention periods, Git history rewrite, long-term archive location, external storage, and release retention.

Do not combine approvals across tiers. Before implementation provide a dry-run list with exact paths, action, current size, expected saving, risk, backup, rollback, required tests, and documentation/version impact.

## Build, QA, and temporary data

Before cleanup check for a related process, recent writes, file locks, reproducibility, and whether release/test gates still need the content. Never remove an active or possibly active workspace.

Builds must stage to `build-next/` and `dist-next/`. A new `dist/` may replace the previous output only after:

1. the build completed successfully;
2. required runtime files exist (`Yeal.exe`, `bin/node.exe`, `bin/ffmpeg.exe`);
3. the finished package contains no binaries sourced from foreign host runtimes;
4. a frozen startup log contains `Yeal UI ready` and no traceback/DLL/QML load error;
5. the old output can be restored if activation fails.

PyInstaller must not inherit unrelated DLLs from Codex, Poppler, libheif, other Python environments, or arbitrary `PATH` entries. Prefer a dedicated minimal build environment outside the repository. The spec must reject foreign runtime sources.

## Runtime data and databases

Without a direct owner request, do not open, copy, compress, rotate, migrate, edit, or delete databases or productive runtime data. First identify producer, reader, meaning, reproducibility, retention, external data path, duplicate-storage risk, and required GUI/function acceptance.

An approved migration follows: preview, owner approval, copy-only migration, functional acceptance, separate deletion approval, source removal.

## Archives, backups, snapshots, and media

Names such as `old`, `backup`, `copy`, a version number, `_snapshots`, or `_to_delete` are review hints, not deletion permission. Before moving or deleting, establish purpose, last stable state, fallback value, current use, external backup, newer equivalent, and hash equality of suspected duplicates.

## Git rules

For a large `.git`, inspect reachable history, loose objects, packfiles, unreachable objects, and large blobs first.

- A normal `git gc` requires explicit owner approval; it may pack objects but must not rewrite history.
- Do not use `git prune`, `--prune=now`, filter-repo/BFG, force-push, or history rewriting without a separate backup and owner decision.
- Do not delete branches, tags, commits, or remotes without explicit approval.
- Do not commit, tag, or push unless authorized by the owner and consistent with `CLAUDE.md`.
- GitHub is not a general backup for generated working directories. Use Releases/Actions artifacts for approved deliverables and keep source history focused on source and documentation.

## Post-change verification and report

After every approved structural measure, remeasure total size, file count, directory count, top-level sizes, `git status`, tracked modifications, untracked files, and the relevant build/test/reproduction path.

Use this report format:

### Problem

Measured inconsistency.

### Analysis

Evidence, sizes, counts, and cause.

### Risk

Technical and data-loss implications.

### Measure

Exact action and expected saving.

### Approval required

The single owner decision still needed.

### Status

`analysed`, `approved`, `implemented`, `verified`, `open`, or `blocked`.

For a full review, provide a reconciled table covering source, tests, documentation, runtime data, databases, build data, program output, QA/temp, archives/backups, Git, and unexplained remainder. The category sum must match the measured total within rounding tolerance.

For a review-only task, explicitly state that no files were changed, deleted, or moved; no data was opened; no process, test, build, migration, commit, tag, push, `git gc`, or prune was performed. If any item did occur, report it accurately instead of using the review-only statement.

## Current baseline (2026-11-08, during v0.9.1.41 work)

Before safe cleanup, the workspace measured approximately 1,238 MB, 4,123 files, and 429 directories. Duplicate APK and failed `build-next`/`dist-next` outputs were then removed. A later measurement was approximately 852 MB, 4,108 files, and 430 directories while another build was starting.

Material findings:

- `.git`: 278.04 MiB in 2,180 loose objects; an explicitly approved normal `git gc` packed this to 151.79 MiB without rewriting history.
- `dist`: about 305 MB, consisting of an obsolete one-file EXE plus intentional Node/FFmpeg copies; replacement is allowed only after the new folder build passes the real startup gate.
- `BIN`: about 154.5 MB after removing one hash-identical duplicate APK alias; the retained versioned APK is an artifact, not source.
- `docs`: about 52.9 MB, mainly tracked media; no automatic cleanup.
- `_to_delete`: about 35.9 MB of archives/screenshots; ignored but not approved for deletion.
- `_snapshots`: about 24.6 MB and owner-controlled; no automatic cleanup.

Final local measurement after the approved cleanup and verified folder build: approximately **768.6 MB, 2,949 files, and 258 directories**. The reduction from the initial 1,238.3 MB measurement is about **469.7 MB (37.9%)**, despite retaining the complete 347.8 MB portable Windows output with Node and FFmpeg. The remaining largest optional review item is `_to_delete` (35.9 MB); it was not deleted because it requires a separate owner decision.

Future reviews compare against this final 2026-11-08 baseline until a newer measured baseline is committed.
