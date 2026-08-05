"""Constants for the FlexGet integration."""

from datetime import timedelta
from typing import Final

DOMAIN: Final = "flexget"
PLATFORMS: Final = ["binary_sensor", "sensor"]

CONF_API_PATH: Final = "api_path"
CONF_TOKEN: Final = "token"
CONF_INSTANCE_NAME: Final = "instance_name"
CONF_SCAN_INTERVAL: Final = "scan_interval"

DEFAULT_API_PATH: Final = "/api"
DEFAULT_PORT: Final = 5050
DEFAULT_SCAN_INTERVAL: Final = 60
MIN_SCAN_INTERVAL: Final = 10
DEFAULT_TIMEOUT: Final = 10

UPDATE_INTERVAL: Final = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

ATTR_API_VERSION: Final = "api_version"
ATTR_LATEST_VERSION: Final = "latest_version"
ATTR_PHASE: Final = "phase"
ATTR_PLUGIN: Final = "plugin"
ATTR_STATE_SINCE: Final = "state_since"
