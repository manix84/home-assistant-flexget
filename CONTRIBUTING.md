# 🤝 Contributing

Thanks for helping make Home Assistant FlexGet better! Contributions of all
sizes are welcome, from documentation fixes to API compatibility improvements.

## 🧭 Before you start

- Search existing issues before opening a new one.
- For large features or behavior changes, open a discussion or feature request
  first so we can agree on scope.
- Read `AGENTS.md` if you use Codex, Copilot, or another coding agent.
- Keep the integration read-only unless a proposal explicitly addresses the
  security and confirmation model for control actions.

## 🛠️ Development setup

```console
python3.13 -m venv .venv
.venv/bin/pip install -r requirements_test.txt
```

Create a focused branch, make your changes, and add tests that demonstrate the
new or corrected behavior.

## ✅ Required checks

```console
.venv/bin/ruff format --check .
.venv/bin/ruff check .
.venv/bin/pytest -q
git diff --check
```

Please also validate any edited JSON with `python -m json.tool`.

## 🧪 What good tests cover

- the successful path and realistic API response shapes;
- authentication, timeout, connection, and malformed-response failures;
- multi-port instances on one host;
- coordinator and entity availability behavior;
- config-flow errors and duplicate suppression;
- credential redaction.

Tests must not contain real credentials or require a public/live FlexGet server.

## 📝 Pull requests

Keep pull requests small and explain:

- what changed and why;
- how it was tested;
- whether live Home Assistant or FlexGet verification was performed;
- any compatibility, security, or privacy implications.

Update `WHATSNEW.md` for user-visible changes and relevant documentation when
behavior changes. Friendly, purposeful emoji are welcome in Markdown. ✨
