# 🔐 Security policy

## Supported versions

Security fixes are applied to the latest released version. Users should upgrade
before reporting a problem that may already be fixed.

## 🚨 Reporting a vulnerability

Please do not open a public issue for a suspected vulnerability or accidentally
exposed credential. Use GitHub's private vulnerability reporting feature on the
repository's **Security** tab.

Include, where possible:

- the affected version or commit;
- a clear description of the impact;
- reproduction steps using fake credentials;
- suggested mitigations or a patch, if available.

Do not include real FlexGet tokens, Home Assistant backups, diagnostics with
private data, or publicly reachable instance details.

## 🛡️ Security expectations

The integration is designed to:

- send tokens only to the configured local FlexGet endpoint;
- redact tokens from diagnostics;
- verify zeroconf hints through authenticated API access;
- keep task controls disabled by default;
- serialize, reread, and verify opt-in task configuration changes;
- avoid daemon-management controls.

See `PRIVACY.md` for the data-handling policy.
