# Changelog

All notable changes to the ESP BLE Bridge add-on will be documented in this file.

## [0.28.0] - 2025-11-26

### 🎉 MAJOR FEATURE: Native Device Pairing

Add BRMesh devices directly from Home Assistant - no Android app required!

### Added

#### New Pairing Tab
- **Device Discovery** - Scan for unpaired devices in pairing mode
- **One-Click Pairing** - Pair devices with mesh key from the web UI
- **Test Controls** - Verify pairing with ON/OFF/Brightness commands
- **Auto-Configuration** - Automatically adds paired devices to your lights list
- **Step-by-Step Guide** - Built-in instructions for factory reset and pairing

#### Protocol Support
- Complete implementation of BRMesh pairing protocol
- Complete implementation of BRMesh control protocol
- Pure Python implementation for reliability

#### API Endpoints
- `GET /api/pairing/discover` - Discover unpaired devices
- `POST /api/pairing/pair` - Pair a device with your mesh network
- `POST /api/control/send` - Send control commands to devices

### Benefits

This release eliminates the need for the Android app during setup:
- Pair multiple lights without manual phone pairing
- Perfect for outdoor/hard-to-reach installations
- Consistent mesh configuration across all devices
- Simplified deployment for multi-property setups

### Documentation

- **PAIRING_GUIDE.md** - Complete pairing instructions
- **QUICK_START.md** - Updated with pairing workflow

## [0.19.0] - 2025-11-25

### Added - Map View Enhancement
- **Tile Layer Selector** - Choose between Satellite, Streets, or Topographic map views
- **Auto-Center** - Map automatically centers on lights when loaded
- **Coordinate Display** - Shows latitude/longitude when hovering over map

### Fixed
- Map initialization now correctly uses `map_latitude` and `map_longitude` from config
- Map center properly syncs with configured location

## [0.18.0] - 2025-11-25

### Added - Controller Management
- **Visit ESPHome** button - Quick link to ESP32 web interface
- **View Logs** button - Direct access to ESPHome device logs
- **Edit Controller** button - Modify controller settings from UI
- **ESPHome Status** - Real-time detection if controller is running ESPHome

### Fixed
- Modal buttons now disable immediately after click to prevent duplicate controllers
- Cache busting for JavaScript and CSS files to ensure updates load properly

## [0.17.0] - 2025-11-25

### Added - Live Logs Viewer
- New "📋 Logs" tab with real-time log streaming
- **Log Level Filter** - View DEBUG, INFO, WARNING, or ERROR messages
- **Category Filter** - Filter by addon, mqtt, ble, esphome categories
- **Auto-Scroll** - Automatically scrolls to newest logs
- **Pause/Resume** - Pause log streaming to analyze specific entries
- **Clear Logs** - One-click log clearing

### Changed
- Version display now shows both addon version and bridge firmware version separately
- Addon version: 0.17.x (features, UI, backend)
- Bridge firmware: 1.0.0 (ESPHome component functionality)

## [0.16.0] - 2025-11-25

### Changed
- Improved logger level to DEBUG for better BLE advertisement visibility
- Enhanced BLE scanner logging to show manufacturer data

### Documentation
- Added comprehensive troubleshooting for BLE detection issues
- Documented factory reset procedures for various light models

## [0.15.0] - 2025-11-25

### Fixed
- Fixed encryption key regeneration breaking HA connections
- API encryption key now only generated once and persisted
- Existing controllers maintain connection after addon restart

### Changed
- Improved controller connection stability
- Better error handling for ESPHome API connections

## [0.14.0] - 2025-11-25

### Added - Enhanced UI
- **Mesh Key Generator** - One-click random mesh key generation
- **Device Address Lookup** - Find next available address automatically
- **Controller Quick Actions** - Edit, visit, and view logs for each controller
- **Map Tile Layer Selector** - Choose between Satellite, Streets, Topographic views

### Fixed
- Map coordinates now properly sync with configured location
- Modal dialogs prevent duplicate submissions

## [0.13.0] - 2025-11-24

### Changed
- **Rebranded to ESP BLE Bridge** - More accurate name reflecting multi-protocol support
- Updated all documentation and UI elements
- Repository renamed to ha-esp-ble-bridge

### Reason
Moved away from "brmesh" branding to avoid trademark concerns and better represent the addon's capabilities.

## [0.12.0] - 2025-11-24

### Added - ESPHome Config Generator
- **Automatic YAML Generation** - Generate optimized ESPHome configs from web UI
- **Optimized Command Sending** - 66% reduction in BLE commands
  - Debouncing (100ms)
  - Command deduplication
  - Minimum interval enforcement (300ms)
- **BLE Scanner Integration** - Auto-detect unpaired devices in pairing mode

### Documentation
- Added AUTOMATIC_YAML_GENERATION.md
- Updated FORK_SUMMARY.md with optimization details

## Earlier Versions

See git history for changes prior to v0.12.0.

---

## Versioning

This project uses [Semantic Versioning](https://semver.org/):
- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

## Credits

- **[@scross01](https://github.com/scross01)** - ESPHome fastcon component
- **[Mooody](https://mooody.me/)** - Protocol analysis
- **[ArcadeMachinist](https://github.com/ArcadeMachinist)** - brMeshMQTT reference
- **Home Assistant Community** - Testing and feedback
