"""Constants for Xbox Dev Mode integration."""

DOMAIN = "xbox_dev_mode"
DEFAULT_PORT = 11443

# Device states
STATE_DEV = "dev_mode"
STATE_RETAIL = "retail"
STATE_OFF = "off"

# Config flow options
CONF_SCAN_INTERVAL = "scan_interval"
CONF_SCREENSHOT_INTERVAL = "screenshot_interval"
CONF_SETTINGS_INTERVAL = "settings_interval"

# Default intervals (in seconds)
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_SCREENSHOT_INTERVAL = 60
DEFAULT_SETTINGS_INTERVAL = 120

# Minimum allowed intervals (in seconds). Screenshot interval has no minimum
# above 0 since 0 intentionally means "off" (see config_flow options schema).
MIN_SCAN_INTERVAL = 5
MIN_SETTINGS_INTERVAL = 5

# Platforms (populated incrementally in B4-B6)
PLATFORMS = ["binary_sensor", "sensor", "select", "switch", "button", "image", "remote"]
