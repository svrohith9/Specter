# CI/CD

## Continuous Integration
- GitHub Actions runs lint + tests on push and PR.
- Workflow: `.github/workflows/ci.yml`

## Releases
- Tag with `vX.Y.Z` to trigger a GitHub Release.
- Workflow: `.github/workflows/release.yml`

## Versioning
- Semantic Versioning is used: MAJOR.MINOR.PATCH
