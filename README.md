# Home Assistant FlexGet

A local-polling Home Assistant custom integration for monitoring one or more
[FlexGet](https://flexget.com/) daemon APIs. Every API endpoint is a separate
config entry and Home Assistant device, so several configurations on the same
host are supported when they use different ports.

## Features

- Manual setup with host, port, API path, and token
- Optional advanced zeroconf discovery through `_flexget._tcp.local.`
- Duplicate suppression by normalized `host:port`
- One shared coordinator request cycle per instance
- Connectivity, version, task count, queue, active task, and update sensors
- Token reauthentication, display-name/token/polling options, and redacted diagnostics
- Read-only API access; the integration cannot execute tasks or manage daemons

## Install

Copy `custom_components/flexget` into Home Assistant's `custom_components`
directory and restart Home Assistant. Add **FlexGet** from
**Settings > Devices & services > Add integration**.

Create an API token in each FlexGet daemon and configure each instance manually
with its host, API port, and token. This is the normal and recommended setup:

1. In Home Assistant, open **Settings > Devices & services**.
2. Select **Add integration**, search for **FlexGet**, and select it.
3. Enter the FlexGet daemon's host, port, API path (normally `/api`), token,
   and a recognizable instance name.
4. Repeat for every daemon. Ports do not need to be consecutive.

The integration sends the token only in the `Authorization: Token ...` header.
Tokens are never exposed as entity attributes or diagnostics.

## Advanced: optional Avahi discovery

FlexGet does not advertise its API by default. Most users should use manual
setup above. If you administer the FlexGet host, you can optionally configure
Avahi to make each daemon appear automatically in Home Assistant. This saves
typing the host and port, but Home Assistant still asks for the API token.

Install Avahi on the FlexGet host, then create one service file per daemon in
`/etc/avahi/services/`. For example, save the following as
`/etc/avahi/services/flexget-anime.service`:

```xml
<?xml version="1.0" standalone="no"?>
<!DOCTYPE service-group SYSTEM "avahi-service.dtd">
<service-group>
  <name replace-wildcards="yes">FlexGet Anime on %h</name>
  <service>
    <type>_flexget._tcp</type>
    <port>5053</port>
    <txt-record>name=Anime</txt-record>
    <txt-record>config=config-download-anime-shows.yml</txt-record>
    <txt-record>path=/api</txt-record>
  </service>
</service-group>
```

Change the display name, port, config filename, and API path for that daemon.
Repeat for every daemon, then restart the advertiser:

```console
sudo systemctl restart avahi-daemon
sudo systemctl status avahi-daemon
```

The instance should then appear as a discovered integration under
**Settings > Devices & services**. If it does not, manual setup remains fully
supported and provides the same entities and behavior.

Discovery records are treated as untrusted hints. Setup completes only after
the user supplies a token and the authenticated version endpoint succeeds.

## Development

Create a Python virtual environment, install `requirements_test.txt`, then run:

```console
pytest
ruff check .
ruff format --check .
```
