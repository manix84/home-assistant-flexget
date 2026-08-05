# 🤖 GitHub Copilot instructions

Read and follow `/AGENTS.md` as the authoritative repository guidance before
suggesting or changing code. Its architecture, security, privacy, testing,
documentation, emoji, and Git standards all apply.

In particular:

- keep one client/coordinator/device per normalized FlexGet `host:port`;
- never expose or log API tokens;
- keep entities read-only and route HTTP through `FlexGetClient`;
- add focused tests and run the validation commands from `AGENTS.md`;
- treat manual configuration as the default and Avahi as optional/advanced;
- use friendly, purposeful emoji in Markdown documentation, not source code or
  commit subjects.
