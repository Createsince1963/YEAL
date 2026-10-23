# Keeping versions safe (rule for every project)

Every version must be stored durably, on GitHub or locally, so old versions can always be compared. Losing code is not acceptable.

For each release:
1. Update `VERSION`, `yeal/__init__.py`, `pyproject.toml` and `CHANGELOG.md` together.
2. Commit, then tag: `git tag -a vX.Y.Z -m "Yeal X.Y.Z"`.
3. Push the branch and the tags: `git push origin main --tags`.
4. Optionally attach the built `Yeal.exe` (under 100 MB) to a GitHub release.
5. Before replacing a file that several coders edit, commit first (or copy it to `_to_delete\` as `<name>.before-<reason>`).

History note: versions 0.1.0 - 0.8.8 were developed before the repository existed and were not saved as separate commits;
their changes are only documented in `CHANGELOG.md`. From 0.8.10 on every version is tagged.
