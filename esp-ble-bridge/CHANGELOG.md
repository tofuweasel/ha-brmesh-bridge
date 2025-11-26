# Changelog

All notable changes to the BRMesh Bridge add-on will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.19.0] - 2025-11-25

### 🔄 Reset & Recovery Package

Complete reset and recovery functionality for lights, controllers, and system configuration.

### Added

#### Reset Operations
- **Factory Reset Light** - Send BLE command to clear pairing data and return light to pairing mode
- **Remove Light (Unpair)** - Remove light from Home Assistant without factory reset
- **Reset Controller** - Remove ESP32 controller from configuration and delete YAML files
- **Full System Reset** - Danger zone feature to remove all lights, controllers, scenes, and effects

#### API Endpoints
- `POST /api/lights/<id>/reset` - Factory reset a specific light
- `POST /api/lights/<id>/unpair` - Remove light from system (preserves mesh pairing)
- `POST /api/controllers/<name>/reset` - Reset controller configuration
- `POST /api/system/reset` - Full system reset (requires double confirmation)

#### UI Controls
- **Reset Button** on each light card in Lights tab
- **Remove Button** on each light card for quick removal
- **Reset Button** on each controller card in Controllers tab
- **Danger Zone** section in Settings tab with Full System Reset
- **Confirmation Dialogs** with clear warnings for destructive operations

#### Documentation
- **RESET_GUIDE.md** - Comprehensive 50+ page reset and recovery guide
  - Factory reset procedures
  - Recovery from accidental deletions
  - Troubleshooting common issues
  - API reference
  - Best practices
  - Common scenarios

### Changed
- Updated version banner to v0.19.0
- Enhanced light card UI with reset/remove actions
- Enhanced controller card UI with reset action
- Improved error handling for reset operations

### Technical Details
- BLE factory reset command: `0xF0 0xFF <light_id> 0x00 0x00 0x00 0x00 0x00`
- MQTT discovery unpublish support (empty payload to remove entities)
- ESPHome YAML file cleanup on controller reset
- Preserves mesh key and MQTT settings during full system reset

### Security
- Double confirmation required for system reset (button + text input "RESET")
- Warning dialogs explain consequences of each action
- Backup recommendations before destructive operations

## [0.18.3] - 2025-11-25

### Added
- ESPHome device picker in "Add Existing Controller" modal
- Controller status badges (Config, Online, Build Ready)
- Persisted esphome_path in controller configuration

## [0.9.0] - 2025-11-24

### 🎉 Beta Release: GUI Configuration & Phone-Free Operation

This is a complete rewrite of the BRMesh Bridge add-on with a focus on user experience and automation.

### Added

#### Web UI & Configuration
- **Complete GUI Configuration** - All settings configurable through web interface, no manual file editing required
- **Settings Tab** - Dedicated interface for mesh key, MQTT, map, and feature configuration
- **Auto-detect Home Assistant Location** - Automatically uses your HA home location for map view
- **Import/Export Configuration** - Backup and restore your complete setup as JSON

#### Light Management
- **BLE Device Discovery** - Automatically scan for and register new lights without phone
- **Phone-Free Operation** - Add 7+ lights without ever touching the Android app
- **Dynamic Light Management** - Add, remove, and rename lights without recompiling ESP32 firmware
- **BRMesh App Sync** - Import device names from Android app via ADB or JSON export

#### Visual & Control
- **Interactive Map View** - Visualize and place lights on satellite imagery (ESRI ArcGIS)
- **8 Built-in Effects** - Rainbow, color loop, twinkle, fire, Christmas, Halloween, strobe, breathe
- **Scene Management** - Create and activate multi-light scenes through GUI
- **Signal Strength Matrix** - Monitor controller-to-light signal strength
- **Drag-and-Drop Placement** - Position lights on map with mouse

#### Advanced Features
- **ESPHome Config Generator** - Automatically generate ESP32 controller configs from HA settings
- **Multi-Controller Support** - Manage multiple ESP32 controllers with automatic light assignment
- **NSPanel Integration** - Optional Nextion display touch interface generation
- **MQTT Auto-Discovery** - Automatic Home Assistant entity creation
- **REST API** - Complete API for programmatic control and integration

#### Developer Experience
- **HACS Compatible** - Ready for Home Assistant Community Store installation
- **Docker Multi-Arch** - Support for ARM, ARM64, AMD64, i386 architectures
- **Comprehensive Documentation** - Quick start, GUI guide, setup guide, deployment guide
- **GitHub Actions** - Automated Docker image building and publishing

### Changed
- **Complete UI Rewrite** - Modern web interface with responsive design
- **Configuration Approach** - GUI-first instead of YAML-first
- **MQTT Integration** - Auto-detects Home Assistant's Mosquitto service by default
- **Map Tiles** - Switched to ESRI ArcGIS (free, no API key required) from OpenStreetMap

### Fixed
- Mesh key now properly sanitized in documentation
- IP addresses and personal information removed from examples
- Default configuration values no longer contain user-specific data

### Security
- All secrets and personal information removed from documentation
- Examples use placeholder values
- No hardcoded credentials or mesh keys in code

### Credits
- **[@scross01](https://github.com/scross01)** - Creator and maintainer of [esphome-fastcon](https://github.com/scross01/esphome-fastcon) ESPHome component
- **[Mooody](https://mooody.me/)** - Original Fastcon BLE protocol reverse engineering
- **[ArcadeMachinist](https://github.com/ArcadeMachinist)** - brMeshMQTT reference implementation
- **Home Assistant Community** - Testing, feedback, and support

### Breaking Changes
- Configuration format has changed - migration from v1.x requires reconfiguration
- Web UI port is now 8099 (was not configurable before)
- MQTT topic structure may have changed for some devices

### Migration Notes
From v1.x to v0.9.0:
1. Export your light IDs and names from old config
2. Install v2.0.0
3. Use Settings tab to reconfigure mesh key and MQTT
4. Use "Add Light" in GUI to recreate your lights
5. Test each light before removing old config

---

## [1.0.0] - 2025-03-XX (Historical)

### Added
- Initial release
- Basic BRMesh light control via MQTT
- Manual light configuration
- Single ESP32 controller support
- Basic on/off and color control

### Known Limitations
- Required manual YAML editing
- No BLE discovery
- No web UI
- Single controller only
- Manual light ID discovery via ADB

---

## Future Releases

### [1.0.0] - Planned
- Full stable release
- Production-ready
- Performance optimizations

### [1.1.0] - Planned
- **Automation Templates** - Pre-built automation examples
- **Grouping** - Create light groups through GUI
- **Effect Builder** - Create custom lighting effects
- **Backup/Restore** - One-click backup to cloud services
- **Mobile App** - Companion mobile app for quick control

### [2.2.0] - Planned
- **Voice Control** - Alexa and Google Home integration
- **Schedules** - Time-based lighting schedules
- **Sunrise/Sunset** - Automatic timing based on location
- **Energy Monitoring** - Track estimated power usage
- **Multi-Language** - i18n support for web UI

### Contributions Welcome!
Have an idea? Submit a feature request or pull request on GitHub!

---

## Version Numbering

- **Major (X.0.0)** - Breaking changes, major new features
- **Minor (x.X.0)** - New features, backwards compatible
- **Patch (x.x.X)** - Bug fixes, minor improvements

---

[0.9.0]: https://github.com/YOUR_USERNAME/ha-brmesh-bridge/releases/tag/v0.9.0
[1.0.0]: https://github.com/YOUR_USERNAME/ha-brmesh-bridge/releases/tag/v1.0.0
