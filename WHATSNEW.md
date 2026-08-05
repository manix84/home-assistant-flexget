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
- Diagnostic-style count sensors with configured, queued, and scheduled task
  names available as attributes instead of measurement-style graph entities.
- Schedule count, accepted-history count, latest version, last accepted task,
  task-running, and update-available entities.
- Reauthentication and options for token, display name, and polling interval.
- Credential-redacted diagnostics.
- HACS metadata, automated tests, linting, and repository validation.
- Local Home Assistant and HACS branding using the official FlexGet icon and
  full-color wordmark.
- Coordinated SemVer checks and automatic Release Please version bumps across
  release metadata and notes.

### 🔐 Security and privacy

- API tokens remain in Home Assistant config-entry storage.
- Tokens are excluded from entities and redacted from diagnostics.
- The integration provides no task execution or daemon-management controls.
- No telemetry, analytics, or cloud service is used.

### 🐛 Fixed

- Discovered FlexGet cards now show the advertised instance purpose, such as
  **Sort**, **TV Shows**, or **Anime**, instead of the generic integration name.
- Zeroconf confirmation titles no longer generate missing-placeholder errors in
  the Home Assistant frontend.

### 📝 Documentation

- Manual setup is documented as the normal path.
- Avahi discovery is documented as an optional advanced convenience with
  explicit service-file instructions.
- Community contribution, conduct, security, support, and privacy guidance has
  been added.
