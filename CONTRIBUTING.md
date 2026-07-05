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
  documented path in the docstring, plus a mocked test. Endpoint wrappers
  return the raw decoded JSON (a `dict`) — the generated Pydantic models are an
  opt-in validation layer callers apply themselves, not the return type.
- New providers: one module under `src/streetworks/`, built on
  `streetworks._transport`, raising `streetworks.exceptions` types.
- **Derived views**: methods that don't map 1:1 to an endpoint but reduce a raw
  response (e.g. `reporting.active_section_58`) follow a convention
  so they're easy to tell apart from raw wrappers:
  - open the docstring with `Derived view:` and state it's computed
    client-side, not a 1:1 API call;
  - group them under a `# --- derived views` heading in the API group;
  - still return a plain `dict`, and validate rows against the relevant
    generated model before reducing (so drifted/malformed data raises).
  Keep the reduction logic in `utils/<thing>_utils.py`, not inline in the
  client (see `streetmanager/utils/section_58_utils.py`).
- Run `ruff check .` before opening a PR.

## Verifying against real services

If you have sandbox credentials for Street Manager or a DataVIA account,
real-world verification of endpoint paths and payloads is hugely valuable —
please note in your PR what you verified and against which environment/version.
