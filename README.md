<p align="center">
  <img src="custom_components/xbox_dev_mode/brand/logo@2x.png" alt="Xbox Dev Mode" height="128">
</p>

# Xbox Dev Mode

[![Tests](https://github.com/hudsonbrendon/ha-xbox-dev-mode/actions/workflows/tests.yml/badge.svg)](https://github.com/hudsonbrendon/ha-xbox-dev-mode/actions/workflows/tests.yml)
[![Hassfest](https://github.com/hudsonbrendon/ha-xbox-dev-mode/actions/workflows/hassfest.yml/badge.svg)](https://github.com/hudsonbrendon/ha-xbox-dev-mode/actions/workflows/hassfest.yml)
[![HACS](https://github.com/hudsonbrendon/ha-xbox-dev-mode/actions/workflows/validate.yml/badge.svg)](https://github.com/hudsonbrendon/ha-xbox-dev-mode/actions/workflows/validate.yml)
[![Release](https://img.shields.io/github/v/release/hudsonbrendon/ha-xbox-dev-mode?sort=semver)](https://github.com/hudsonbrendon/ha-xbox-dev-mode/releases)
[![Downloads](https://img.shields.io/github/downloads/hudsonbrendon/ha-xbox-dev-mode/total)](https://github.com/hudsonbrendon/ha-xbox-dev-mode/releases)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-2024.12.0%2B-18BCF2?logo=homeassistant&logoColor=white)](https://www.home-assistant.io/)
[![License](https://img.shields.io/github/license/hudsonbrendon/ha-xbox-dev-mode)](LICENSE)

Xbox Dev Mode integration for Home Assistant. Monitor and control Xbox consoles running in Developer Mode.

## Important: Developer Mode Only

This integration **only works with Xbox consoles in Developer Mode**. Developer Mode is a special boot mode where the console operates differently from retail mode:

- Developer Mode **disables retail games and Game Pass**
- To switch to Developer Mode, the console must be rebooted into an alternate OS boot environment
- Switching between Retail and Developer mode requires a console restart
- This is a **one-way per boot** — you must explicitly boot into Dev Mode each time

If your console boots into retail mode, you'll see only the device powered off until it boots into Developer Mode again.

## Features

- Monitor console state: Off, Retail, or Developer Mode
- Real-time telemetry: CPU load, memory usage, GPU memory
- Foreground app detection
- Screenshot capture
- Sideloaded app management
- Device settings control (resolution, HDR, VRR, ALLM, etc.)
- App launch and termination via services
- File upload to app storage
- Setting adjustment

## Installation

[![Open in HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=hudsonbrendon&repository=ha-xbox-dev-mode&category=integration)
[![Add integration](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=xbox_dev_mode)

### Via HACS (Recommended)

1. Install HACS if you haven't already
2. Go to HACS > Integrations
3. Click "Explore & Download Repositories"
4. Search for "Xbox Dev Mode"
5. Install the integration
6. Restart Home Assistant
7. Go to Settings > Devices & Services > Integrations > Create Integration
8. Search for "Xbox Dev Mode" and follow the configuration flow

### Manual Installation

1. Copy the `custom_components/xbox_dev_mode` folder to your `custom_components` directory
2. Restart Home Assistant
3. Go to Settings > Devices & Services > Integrations > Create Integration
4. Search for "Xbox Dev Mode" and follow the configuration flow

## Configuration

You'll need:

- **Host**: The IP address of your Xbox console
- **Username**: Xbox Developer Account username (default: "developer")
- **Password**: Xbox Developer Account password
- **Port**: Device Portal port (default: 11443)

Optional settings:

- **Scan Interval**: How often to refresh device state (default: 30 seconds)
- **Screenshot Interval**: How often to capture screenshots (default: 60 seconds, 0 = disabled)
- **Settings Interval**: How often to fetch device settings (default: 120 seconds)

## Entities

### Binary Sensors

| Entity | Description |
|--------|-------------|
| `binary_sensor.xbox_dev_mode` | Device connectivity status |

### Sensors

| Entity | Description |
|--------|-------------|
| `sensor.xbox_console_state` | Console state: dev_mode, retail, or off |
| `sensor.xbox_foreground_app` | Currently running app name |
| `sensor.xbox_cpu_load` | CPU load percentage |
| `sensor.xbox_memory_used` | Used memory in MB |
| `sensor.xbox_memory_available` | Available memory in MB |
| `sensor.xbox_gpu_memory_used` | GPU memory used in MB |
| `sensor.xbox_sideloaded_apps` | Count of sideloaded applications |
| `sensor.xbox_sandbox` | Sandbox identifier |
| `sensor.xbox_os_version` | Operating system version |

### Image

| Entity | Description |
|--------|-------------|
| `image.xbox_screen` | Console screenshot (when enabled) |

### Select

| Entity | Description |
|--------|-------------|
| `select.xbox_app` | Select which sideloaded app to control |
| `select.xbox_tv_resolution` | Change TV resolution |
| `select.xbox_power_mode` | Power mode setting |
| `select.xbox_hdmi_audio` | HDMI audio format |
| `select.xbox_color_space` | Color space setting |
| `select.xbox_headset_format` | Headset audio format |
| `select.xbox_default_app` | Default app on boot |

### Switches

| Entity | Description |
|--------|-------------|
| `switch.xbox_allow_hdr` | Enable/disable HDR |
| `switch.xbox_allow_4k` | Enable/disable 4K |
| `switch.xbox_allow_vrr` | Enable/disable VRR |
| `switch.xbox_allow_allm` | Enable/disable ALLM |

### Buttons

| Entity | Description |
|--------|-------------|
| `button.xbox_launch_app` | Launch selected sideloaded app |
| `button.xbox_terminate_foreground` | Terminate running app |
| `button.xbox_restart` | Restart console |
| `button.xbox_shutdown` | Shut down console |

## Services

### install_package

Install an app package (.appx file) on the console.

**Service**: `xbox_dev_mode.install_package`

**Parameters**:
- `path` (required): Absolute path to the .appx file (must be within Home Assistant config directory)

### uninstall_package

Uninstall an app package from the console.

**Service**: `xbox_dev_mode.uninstall_package`

**Parameters**:
- `package_full_name` (required): Full package identifier

### launch

Launch a sideloaded app.

**Service**: `xbox_dev_mode.launch`

**Parameters**:
- `package_full_name` (required): Full package identifier

### terminate

Terminate a running app.

**Service**: `xbox_dev_mode.terminate`

**Parameters**:
- `package_full_name` (required): Full package identifier

### upload_file

Upload a file to app storage.

**Service**: `xbox_dev_mode.upload_file`

**Parameters**:
- `package_full_name` (required): Full package identifier
- `subdir` (required): Subdirectory (e.g., "documents", "pictures")
- `path` (required): Absolute path to file (must be within Home Assistant config directory)

### set_setting

Change a device setting.

**Service**: `xbox_dev_mode.set_setting`

**Parameters**:
- `name` (required): Setting name (e.g., "TVResolution")
- `value` (required): New value

## Security Notice

⚠️ **Important**: The Xbox Developer Portal uses:

- **Basic Authentication** (username/password in HTTP header)
- **Self-signed TLS certificate** (HTTPS)

**Use this integration only on trusted local networks.** Do not expose the Device Portal to the internet or untrusted networks.

The password is stored in your Home Assistant configuration and automatically redacted in diagnostics and logs.

## Troubleshooting

### Integration not connecting

1. Verify your Xbox is in Developer Mode (check console boot screen)
2. Confirm the IP address is correct
3. Ensure your Home Assistant network can reach the Xbox
4. Check that the username and password are correct
5. Verify the Device Portal is enabled on the Xbox

### Screenshot not capturing

- Screenshot interval is set to 0 (disabled)
- Device Portal may have rate-limited screenshot requests
- Try increasing the screenshot interval

### Settings not updating

- Settings interval is set to 0 (disabled)
- Some settings are read-only on your console version
- Check Home Assistant logs for errors

## Support

For issues, feature requests, or contributions, visit:
https://github.com/hudsonbrendon/ha-xbox-dev-mode

## License

MIT
