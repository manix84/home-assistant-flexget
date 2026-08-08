# 🛡️ Privacy

Home Assistant FlexGet provides local monitoring and optional local task
controls. It does not provide telemetry, analytics, advertising, or cloud
services.

## 📦 Data the integration stores

Each Home Assistant config entry stores:

- the configured FlexGet host and API port;
- the API base path;
- the API token;
- the instance display name;
- the polling interval.
- whether task controls are enabled.

This information remains in Home Assistant's config-entry storage. The API
token is required for authenticated requests and is never exposed as an entity
state or attribute.

## 🔄 Data the integration processes

The integration periodically requests FlexGet version, configured-task, and
queue/activity data from the endpoint selected by the user. It exposes derived
monitoring entities in Home Assistant, including versions, task counts, active
task details, and the last successful update time.
Slower diagnostic polling also reads task execution summaries, retry failures,
schedule runtime details, and pending-approval totals when those endpoints are
available. Entry titles and failure reasons may appear in diagnostic attributes;
entry URLs and raw log, configuration, variable, and crash-report contents are
not collected.
Recent execution records are aggregated locally into 24-hour counts and rates;
individual historical execution records are not exposed as Home Assistant state.
Optional plugin, IRC, series, and managed-list endpoints are reduced to numeric
inventory and connection-health totals. Plugin names, IRC servers and channels,
list names, and series or movie titles are not exposed as states, attributes, or
diagnostics.

When task controls are explicitly enabled, the integration reads full task
configuration objects to determine each task's `manual` setting. These objects
are processed in memory and are not exposed in entities or diagnostics. A switch
change sends the latest task configuration back to FlexGet after setting only
the task-level `manual` value. Task buttons send the selected task name and only
the explicitly selected normal, interval-bypassing, or learn execution mode to
the FlexGet execution API. Learn mode changes FlexGet's remembered-entry state.
FlexGet may reformat its YAML file or remove comments when its configuration API
writes a task.

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
