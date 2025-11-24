# BRMesh Bridge Home Assistant Add-on Repository

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

Bridge BRMesh/Fastcon BLE lights to Home Assistant with GUI configuration, BLE discovery, effects engine, and phone-free operation.

## About

This repository contains the BRMesh Bridge add-on for Home Assistant, which enables control of BRMesh/Fastcon protocol BLE lights through MQTT, with advanced features including:

- **GUI Configuration** - All settings through web interface, no YAML editing required
- **BLE Discovery** - Find lights without the phone app
- **Effects Engine** - Built-in animations (rainbow, fire, twinkle, etc.)
- **Map View** - Visualize light and controller locations
- **ESPHome Generation** - Auto-generate ESP32 controller configs
- **Multi-Controller** - Support multiple ESP32 controllers
- **NSPanel Integration** - Optional Nextion display support

## Add-ons

This repository contains the following add-on:

### [BRMesh Bridge Pro](./brmesh-bridge)

Control BRMesh/Fastcon BLE lights through Home Assistant with advanced features and GUI configuration.

![Supports aarch64 Architecture][aarch64-shield]
![Supports amd64 Architecture][amd64-shield]
![Supports armhf Architecture][armhf-shield]
![Supports armv7 Architecture][armv7-shield]
![Supports i386 Architecture][i386-shield]

## Installation

1. Click the button below to add this repository to Home Assistant:

   [![Add Repository](https://my.home-assistant.io/badges/supervisor_add_addon_repository.svg)](https://my.home-assistant.io/redirect/supervisor_add_addon_repository/?repository_url=https://github.com/tofuweasel/ha-brmesh-bridge)

   Or manually:
   - Go to **Settings** → **Add-ons** → **Add-on Store**
   - Click **⋮** (menu) → **Repositories**
   - Add: `https://github.com/tofuweasel/ha-brmesh-bridge`
   - Click **Add** → **Close**

2. Find "BRMesh Bridge Pro" in the add-on store and click **Install**

3. Start the add-on and open the Web UI to configure

## Documentation

- [Quick Start Guide](./brmesh-bridge/QUICK_START.md) - Get started in 5 minutes
- [GUI Configuration Guide](./brmesh-bridge/GUI_CONFIGURATION.md) - Complete configuration reference
- [Setup Guide](./brmesh-bridge/SETUP_GUIDE.md) - Detailed setup instructions
- [Changelog](./brmesh-bridge/CHANGELOG.md) - Version history

## Credits

This add-on uses the [esphome-fastcon](https://github.com/scross01/esphome-fastcon) component by [@scross01](https://github.com/scross01) for ESPHome integration with BRMesh/Fastcon protocol lights.

## Support

If you find this add-on useful, please consider starring the repository!

For issues and feature requests, please use the [GitHub issue tracker](https://github.com/tofuweasel/ha-brmesh-bridge/issues).

[aarch64-shield]: https://img.shields.io/badge/aarch64-yes-green.svg
[amd64-shield]: https://img.shields.io/badge/amd64-yes-green.svg
[armhf-shield]: https://img.shields.io/badge/armhf-yes-green.svg
[armv7-shield]: https://img.shields.io/badge/armv7-yes-green.svg
[i386-shield]: https://img.shields.io/badge/i386-yes-green.svg
