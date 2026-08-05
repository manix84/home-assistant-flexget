# 🤖 Agent guide for Home Assistant FlexGet

This file defines the working standards for AI coding agents, including Codex
and GitHub Copilot. Follow it for every change in this repository.

## 🎯 Project mission

Build a dependable, privacy-respecting Home Assistant integration that monitors
multiple FlexGet daemon APIs. Each `host:port` is an independent config entry
and device. The first releases are deliberately read-only.

Optimize for correctness, security, predictable Home Assistant behavior, and
maintainable code—not maximum feature count.

## 🧭 How to work

1. Read this file, the relevant implementation, and nearby tests before editing.
2. Check `git status` and preserve changes that do not belong to the current task.
3. Use a focused feature branch. Push it early when remote access is authorized.
4. If a new multi-stage request follows completed work, commit the current
   checkpoint before beginning the next stage.
5. Make the smallest coherent change that fully solves the request.
6. Add or update tests for changed behavior, including failure paths.
7. Run the checks in [Validation](#-validation) and fix the underlying issue.
8. Review the final diff for secrets, unrelated changes, generated files, and
   accidental regressions before committing.

Never discard, overwrite, or reformat unrelated user work. Never rewrite Git
history or force-push unless explicitly requested.

## 🏗️ Architecture standards

- Keep one Home Assistant config entry, API client, and coordinator per FlexGet
  daemon endpoint.
- Treat normalized `host:port` as the unique ID until FlexGet provides a stable
  server identifier. Do not assume ports are consecutive.
- Route all HTTP calls through `FlexGetClient`; entities must not make requests.
- Fetch shared data once per coordinator update and expose normalized models to
  entities.
- Keep parsing of external responses defensive and isolated in `models.py`.
- Keep entity IDs stable and group all entities beneath the instance device.
- Prefer async Home Assistant APIs and the shared Home Assistant aiohttp session.
- Use config entries for credentials and mutable options for token/name/polling
  changes. Do not introduce YAML configuration.
- Preserve availability isolation: one failed daemon must not affect another.
- Keep control actions, task execution, and daemon management out of scope until
  they are deliberately designed, secured, and approved.

## 🔐 Security and privacy

- Authenticate every API request with `Authorization: Token ...`.
- Never log, interpolate into errors, expose as attributes, commit, or include
  API tokens in diagnostics, fixtures, screenshots, or examples.
- Redact credentials from every diagnostic structure, including options.
- Treat zeroconf/Avahi records as untrusted hints and verify them through the
  authenticated version endpoint.
- Do not scan networks or arbitrary port ranges. Any future discovery probing
  must be explicit, bounded, and initiated by the user.
- Keep the integration free of telemetry, analytics, advertising, and external
  cloud dependencies.
- Use obviously fake values such as `secret-token` in tests and documentation.

Read `PRIVACY.md` before adding data collection, new network destinations, or
diagnostic fields. Update it whenever privacy behavior changes.

## 🐍 Python and Home Assistant style

- Target the Python and Home Assistant versions declared in `pyproject.toml`
  and `requirements_test.txt`.
- Use modern type annotations throughout. Avoid `Any` unless an external API
  boundary genuinely requires it.
- Prefer small functions, immutable dataclasses for normalized data, descriptive
  names, and early validation.
- Use Home Assistant entity descriptions, translation keys, device classes, and
  coordinator entities where appropriate.
- Keep user-facing strings in `strings.json` and mirror English translations in
  `translations/en.json`.
- Distinguish timeout, connection, authentication, unsupported API, and malformed
  response errors in config flows.
- Trigger reauthentication for an expired/rejected token without exposing it.
- Do not add dependencies when the standard library, aiohttp, or Home Assistant
  already provides the needed capability.
- Keep lint suppressions narrow and explain any non-obvious exception.

## 🧪 Testing standards

Tests should be deterministic, fast, and network-independent except for local
aiohttp test servers. Cover the behavior users rely on, not implementation trivia.

Every relevant change should consider:

- successful and rejected token authentication;
- normalized hosts, paths, and multi-port uniqueness;
- timeout, connection, unsupported API, and malformed-response handling;
- multiple instances remaining isolated;
- coordinator normalization and unavailable behavior;
- token redaction in data and options;
- config, reauthentication, options, and zeroconf flows;
- stable entity values, attributes, availability, IDs, and device grouping.

Mock external FlexGet APIs. Never use a real token or depend on a live daemon in
unit tests. Document live torBox verification separately when it is performed.

## ✅ Validation

Run these before handing off code:

```console
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest -q
git diff --check
```

Also validate edited JSON with `python -m json.tool`. For release or metadata
changes, ensure the HACS validation workflow remains valid. If a check cannot be
run, state exactly why and what was run instead.

## 📝 Documentation and emoji style

Documentation should feel friendly, human, and easy to scan. Use relevant emoji
in headings, short callouts, and occasional list markers so documents do not feel
stiff. Keep them purposeful and accessible:

- prefer one meaningful emoji over decorative clusters;
- keep heading text descriptive so meaning never depends on the emoji;
- do not put emoji in code, identifiers, filenames, logs, translations, commit
  subjects, or technical values;
- do not let emoji obscure security warnings or procedural steps;
- keep Markdown CommonMark-compatible with blank lines around lists and headings.

Manual configuration is the normal setup path. Describe Avahi/zeroconf as an
optional advanced convenience and always provide explicit manual instructions.

Update `WHATSNEW.md` for user-visible changes. Update `README.md`, `PRIVACY.md`,
`SECURITY.md`, and translations whenever the change affects their promises.

## 💬 Communication and commits

- Lead handoffs with the outcome, then verification and any remaining limits.
- Be direct about assumptions, unverified live behavior, and blockers.
- Use concise, imperative commit subjects without emoji, for example:
  `Add zeroconf config flow tests`.
- Keep commits focused and reviewable. Do not mix cleanup with behavior changes
  unless the cleanup is required for the change.
- Never claim live FlexGet or Home Assistant validation unless it actually ran.

When uncertain, favor the safer read-only behavior and ask before expanding the
integration's authority. 🛡️
