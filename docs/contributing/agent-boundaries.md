# Agent boundaries

> New content, not a migration — not in README.md (see
> `docs/migration-reconciliation.md`, Case 3: "Agent boundaries", listed
> there as living in project-conventions/CLAUDE.md-adjacent material
> rather than the README). No `CLAUDE.md` or `AGENTS.md` currently
> exists in this repository to migrate from, so this page is the first
> place these rules are written down. **Recorded on the project owner's
> own authority as stated ground rules for how an AI coding agent should
> work on this project, not derived from any file that already
> encoded them.**

Rules for any AI agent (or anyone else) working on this codebase,
particularly when investigating a new data provider:

- **No government accounts.** Don't register for, or use, an account
  under any government or institutional identity to access a data
  source — investigate what's genuinely available without
  authentication, or with credentials the project owner has explicitly
  provided (see [`docs/contributing/scaffolds.md`](scaffolds.md)'s
  "Credentials wanted" state for how the project handles sources it
  doesn't yet have access to).
- **No terms-of-service acceptance on the project's behalf.** Don't
  click through or agree to a provider's ToS, developer agreement, or
  similar in order to unlock access. If a source needs that, it stays a
  documented, unavailable scaffold rather than being worked around.
- **No WAF or bot-protection circumvention.** If a source blocks
  automated access, that's a real, reportable finding (as with the
  `data.nap.imet.gr` TLS-handshake-hang noted for Greece in
  [`docs/providers/europe.md`](../providers/europe.md)) — not something
  to route around with header spoofing, proxies, or similar.

These sit alongside, and are enforced the same way as, this project's
existing data-integrity rules (never silently reproject a CRS, never
infer unstated identifiers, never synthesise entities a source doesn't
publish — see [`docs/concepts/data-integrity.md`](../concepts/data-integrity.md)):
both are about not overstepping what a source has actually, verifiably
given this project permission to do.
