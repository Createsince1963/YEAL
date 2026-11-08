# Keeping versions safe (rule for every project)

Every version must be stored durably, on GitHub or locally, so old versions can always be compared. Losing code is not acceptable.
Owner rules: OR-001 and OR-002 in [13_OWNER_RULES.md](13_OWNER_RULES.md).

## Interim versions (current rule, 0.9.1.NN)
Before every larger or risky change:
1. Snapshot the current state: `_snapshots\<date>_v<version>_<reason>\`.
2. Raise the interim version by one (`0.9.1.NN`, last part two digits) until the owner names the next jump (e.g. 0.9.2).
   Update `VERSION`, `yeal/__init__.py`, `pyproject.toml` and `CHANGELOG.md` together.
3. Test, then commit locally and tag: `git tag -a vX.Y.Z.NN -m "Yeal X.Y.Z.NN"`.
4. **Do not push interim versions.** Push (`git push origin main --tags`) only versions the owner names, and only when the owner says so (`Push_Tags.bat`).
5. Do not build an EXE unasked (OR-003). Optionally attach a built `Yeal.exe` (under 100 MB) to a GitHub release when the owner asks.
6. Before replacing a file that several coders edit, commit first (or copy it to `_to_delete\` as `<name>.before-<reason>`). Never touch changes that are not yours.

## History note
Versions 0.1.0 - 0.8.8 were developed before the repository existed and were not saved as separate commits; their changes are only documented in `CHANGELOG.md`.
From 0.8.10 on every version is tagged. (Until 0.8.x every release was pushed; this was replaced by the interim-version rule on 2026-10-25.)
