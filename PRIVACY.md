# 🛡️ Privacy

Home Assistant FlexGet is a local, read-only integration. It does not provide
telemetry, analytics, advertising, or cloud services.

## 📦 Data the integration stores

Each Home Assistant config entry stores:

- the configured FlexGet host and API port;
- the API base path;
- the API token;
- the instance display name;
- the polling interval.

This information remains in Home Assistant's config-entry storage. The API
token is required for authenticated requests and is never exposed as an entity
state or attribute.

## 🔄 Data the integration processes

The integration periodically requests FlexGet version, configured-task, and
queue/activity data from the endpoint selected by the user. It exposes derived
monitoring entities in Home Assistant, including versions, task counts, active
task details, and the last successful update time.

Requests go directly from Home Assistant to the configured FlexGet endpoint.
The integration does not intentionally send this data anywhere else.

## 📡 Optional discovery

If the administrator separately configures Avahi, Home Assistant may receive a
service name, host, port, API path, and descriptive TXT properties. Discovery
is optional and is treated as an untrusted hint. No token is advertised, and
the endpoint must pass authenticated validation before setup completes.

## 🩺 Diagnostics and logs

Diagnostics include sanitized config-entry details and the latest normalized
coordinator data. Tokens in both entry data and options are redacted.

The integration does not intentionally log authorization headers or tokens. A
user should still review diagnostics and logs before sharing them because host
names, ports, instance names, task names, and activity may be personally
sensitive.

## 🗑️ Removing data

Removing a FlexGet integration entry from Home Assistant removes its stored
connection settings and token through Home Assistant's normal config-entry
management. Home Assistant may retain historical entity data according to the
user's Recorder and backup settings; manage those through Home Assistant.

## 📬 Questions and changes

Open a public issue for general privacy questions that contain no private data.
Use the private process in `SECURITY.md` for sensitive reports. Material changes
to data collection or network behavior must be documented here before release.
