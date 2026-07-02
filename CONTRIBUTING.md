# Contributing

Thanks for your interest in improving `streetworks`!

## Getting started

```bash
git clone https://github.com/KFergusonUK/streetworks
cd streetworks
pip install -e ".[dev]"
pytest
```

## Ground rules

- All tests must run **without credentials** — mock HTTP with `respx`.
- New endpoints: add a typed method to the relevant API group, with the
  documented path in the docstring, plus a mocked test.
- New providers: one module under `src/streetworks/`, built on
  `streetworks._transport`, raising `streetworks.exceptions` types.
- Run `ruff check .` before opening a PR.

## Verifying against real services

If you have sandbox credentials for Street Manager or a DataVIA account,
real-world verification of endpoint paths and payloads is hugely valuable —
please note in your PR what you verified and against which environment/version.
