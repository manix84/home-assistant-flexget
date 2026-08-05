# 🎉 What's new

This file highlights user-visible changes. For the complete commit history, see
the repository's Git history and release notes.

## 🚧 0.1.0 — Unreleased

The first Home Assistant FlexGet release introduces local, read-only monitoring
for multiple daemon instances.

### ✨ Added

- One config entry and Home Assistant device per FlexGet `host:port`.
- Manual setup with normalized host, port, API path, token, and instance name.
- Optional advanced Avahi/zeroconf discovery with authenticated confirmation.
- Shared coordinator polling for version, task, and queue endpoints.
- Connectivity, installed version, configured task count, queued task count,
  active task, and last successful update entities.
- Active-task phase, plugin, and unchanged-state timestamp attributes.
- Reauthentication and options for token, display name, and polling interval.
- Credential-redacted diagnostics.
- HACS metadata, automated tests, linting, and repository validation.

### 🔐 Security and privacy

- API tokens remain in Home Assistant config-entry storage.
- Tokens are excluded from entities and redacted from diagnostics.
- The integration provides no task execution or daemon-management controls.
- No telemetry, analytics, or cloud service is used.

### 📝 Documentation

- Manual setup is documented as the normal path.
- Avahi discovery is documented as an optional advanced convenience with
  explicit service-file instructions.
- Community contribution, conduct, security, support, and privacy guidance has
  been added.
