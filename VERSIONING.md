# Versioning Strategy

## Two Independent Versions

### 1. Addon Version (config.yaml)
- **Current**: v0.27.0
- **Scope**: Home Assistant addon UI, web interface, API endpoints
- **Changes**: UI improvements, new features, bug fixes in the web app
- **Location**: `config.yaml` and `templates/index.html`

### 2. Bridge Firmware Version (ESPHome)
- **Current**: v1.0.0
- **Scope**: ESP32 firmware protocol, BLE communication, light control
- **Changes**: ESPHome YAML template updates, fastcon protocol changes
- **Location**: `esphome_generator.py` constant `BRIDGE_FIRMWARE_VERSION`

## Why Separate Versions?

The addon (web UI) can add features like new UI panels, map views, or settings pages without requiring ESP32 firmware updates. Conversely, protocol improvements or BLE optimizations require firmware updates but don't affect the addon.

## Version Check Flow

1. User opens ESP BLE Bridge addon in Home Assistant
2. UI displays running controllers with status badges
3. For each online controller:
   - Fetches `/api/esphome/status/<controller_name>`
   - Compares `firmware_version` (from ESP32) vs `expected_version` (from addon)
   - Shows ⚠️ warning if versions don't match
4. User can regenerate YAML and rebuild firmware to update

## Updating Versions

### When to bump Addon version:
- New UI features (map, charts, settings pages)
- API endpoint changes
- Bug fixes in web interface
- Import/export functionality changes

**Update**: `config.yaml` version field

### When to bump Firmware version:
- Changes to ESPHome YAML template
- BLE protocol updates
- fastcon component updates
- New light features (effects, scenes, music mode)

**Update**: `esphome_generator.py` → `BRIDGE_FIRMWARE_VERSION` constant

## Compatibility Matrix

| Addon Version | Compatible Firmware | Notes |
|---------------|-------------------|-------|
| 0.27.0        | 1.0.0             | Initial versioned release |

## Standalone App Future

When this becomes a standalone desktop/mobile app:
- Addon version becomes irrelevant
- Bridge firmware version remains authoritative
- App version will be separate (e.g., "ESP BLE Bridge App v2.1.0, FW v1.0.0")
