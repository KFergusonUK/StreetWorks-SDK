# Releasing streetworks

## One-time setup

1. **PyPI Trusted Publishing** (no API tokens to manage):
   - Create a PyPI account and go to
     https://pypi.org/manage/account/publishing/
   - Add a "pending publisher": project `streetworks`,
     owner `KFergusonUK`, repository `StreetWorks-SDK`,
     workflow `publish.yml`, environment `pypi`.
   - In GitHub: Settings → Environments → New environment → `pypi`
     (optionally add yourself as a required reviewer for release protection).
2. **Branch protection** (recommended): Settings → Branches → protect `main`,
   require the CI check to pass.

## Each release

1. Update `version` in `pyproject.toml` and move CHANGELOG entries out of
   "unreleased".
2. Commit and push to `main`; wait for CI to go green.
3. GitHub → Releases → "Draft a new release" → create tag `vX.Y.Z` →
   "Publish release".
4. The `publish.yml` workflow builds and uploads to PyPI automatically.

## Regenerating Street Manager models

Run the **Regenerate Street Manager models** workflow from the Actions tab
(pick the API version). It downloads the official swagger specs, regenerates
the Pydantic models, runs the test suite, and opens a PR for review.

If the default spec URL template ever changes, the correct swagger.json links
are listed on the DfT API specification page for each version.
