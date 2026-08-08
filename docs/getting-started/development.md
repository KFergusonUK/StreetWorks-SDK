# Development

> Migrated verbatim from README.md's `## Development` section (phase one,
> lossless restructure — see `docs/migration-mapping.md`).

```bash
pip install -e ".[dev]"
pytest                    # mocked unit tests - no credentials needed
ruff check .
```

The unit tests mock the network so they run offline and without credentials.
To verify the SDK against the **real** test/sandbox systems with your own
credentials, use the smoke test or the integration suite — see
[docs/INTEGRATION.md](../INTEGRATION.md):

```bash
python scripts/smoke_test.py     # one read-only call per configured service
pytest -m integration -v         # same checks, in the test suite
```
