# GUI Configuration Guide

Complete guide to configuring BRMesh Bridge through the web interface - no manual file editing required!

## Table of Contents

1. [Accessing the Web UI](#accessing-the-web-ui)
2. [Settings Tab Overview](#settings-tab-overview)
3. [Core Settings](#core-settings)
4. [MQTT Configuration](#mqtt-configuration)
5. [Map Configuration](#map-configuration)
6. [Feature Toggles](#feature-toggles)
7. [Import/Export](#importexport)
8. [Adding Lights](#adding-lights)
9. [Creating Scenes](#creating-scenes)
10. [Managing Controllers](#managing-controllers)

---

## Accessing the Web UI

1. Install the BRMesh Bridge add-on in Home Assistant
2. Start the add-on
3. Click "Open Web UI" button
4. The dashboard opens with multiple tabs: Map, Lights, Effects, Scenes, Controllers, Settings

**Port**: 8099 (configurable in add-on options)

---

## Settings Tab Overview

The Settings tab is your central configuration hub. Click the ⚙️ icon in the navigation bar to access it.

All settings are saved to `/data/options.json` automatically - you never need to edit files manually!

---

## Core Settings

### Mesh Key

**Location**: Settings → Core Settings → Mesh Key

The 8-character hexadecimal key that authenticates with your BRMesh lights.

**How to find it**:

```bash
# Connect Android device with BRMesh app installed
adb logcat -c
# Open BRMesh app and control any light
adb logcat -d | grep "jyq_helper"
# Look for: key: 30323336
```

**Example**: `a1b2c3d4` (8 hex characters)

**Important**: This is THE critical setting - without it, no lights will respond!

---

## MQTT Configuration

### Use Home Assistant's MQTT Service (Recommended)

**Location**: Settings → MQTT Configuration → Checkbox

✅ **Checked** (default): Automatically uses Home Assistant's `core-mosquitto` service
- No manual configuration needed
- Auto-detects credentials from environment variables
- Just works!

❌ **Unchecked**: Use external MQTT broker
- Reveals fields for custom MQTT host, port, username, password
- Use this if you have a separate MQTT broker

### Custom MQTT Settings

Only visible when "Use Home Assistant's MQTT service" is unchecked:

- **MQTT Broker Host**: IP or hostname (e.g., `mqtt.example.com`)
- **MQTT Port**: Usually `1883` (unencrypted) or `8883` (TLS)
- **MQTT Username**: Authentication username
- **MQTT Password**: Authentication password

**Default**: Uses Home Assistant's service automatically - no configuration needed!

---

## Map Configuration

### Enable Map View

**Location**: Settings → Map Configuration → Checkbox

Controls whether the Map tab shows your property layout.

### Property Coordinates

**Auto-Detection** ✨: If you have a home location configured in Home Assistant, the add-on will automatically detect and use it when you first start! No manual entry needed.

**Manual Entry** (if auto-detection didn't work):

1. Open Google Maps
2. Right-click your property
3. Click the coordinates at the top to copy them
4. Paste into **Latitude** and **Longitude** fields

**Example**:
- Latitude: `37.774929`
- Longitude: `-122.419416`

The add-on checks Home Assistant's configuration on first run and automatically populates these fields if you've set a home location in HA.

### Zoom Level

Slider from 15-20:
- **15**: Neighborhood view
- **18**: High detail (default, recommended)
- **20**: Maximum zoom

The map uses **ESRI ArcGIS** satellite imagery - free, no API key required!

---

## Feature Toggles

### MQTT Auto-Discovery

✅ Automatically creates Home Assistant entities for all lights
- Lights appear in HA without manual YAML configuration
- Recommended: Leave enabled

### Auto-generate ESPHome Configurations

✅ Generates ESP32 controller YAML files from Home Assistant settings
- Makes HA the "source of truth"
- Download configs from Controllers tab
- Recommended: Leave enabled

### BLE Device Discovery

✅ Scan for new BRMesh lights via Bluetooth
- **Phone-free light addition!**
- Click "Scan for Lights" on Lights tab
- Automatically registers new devices
- Recommended: Leave enabled

### NSPanel UI Integration

Generate Nextion display commands for NSPanel touch screens:

1. Check "NSPanel UI Integration"
2. Enter **NSPanel Entity ID** (e.g., `climate.nspanel_living_room`)
3. Interface automatically updates with light controls
4. Touch to control lights

**Optional**: Only enable if you have an NSPanel device.

---

## Import/Export

### Import from BRMesh App

Sync device names from the Android app:

**Method 1: JSON Export (Recommended)**

1. Export configuration from BRMesh app to JSON file
2. Copy file to Home Assistant's `/share/` directory
3. Set **BRMesh App Export Path** to file location
4. Click **📱 Import from App**

**Method 2: ADB Logcat**

1. Connect Android device via ADB
2. Click **📱 Import from App**
3. Add-on captures logcat and extracts light IDs/names

### Export Configuration

Click **💾 Export Configuration** to download complete settings as JSON:

```json
{
  "mesh_key": "30323336",
  "controllers": [...],
  "lights": {...},
  "scenes": [...],
  "settings": {...}
}
```

**Use cases**:
- Backup before major changes
- Share configuration with others
- Migrate to new Home Assistant instance

---

## Adding Lights

### Automatic Discovery (Phone-Free!)

1. **Power on new light** (press button until it blinks rapidly)
2. Go to **Lights tab**
3. Click **🔍 Scan for Lights**
4. Wait 30 seconds for scan to complete
5. New lights appear automatically!
6. Click light name to rename

**No phone required!** This is the recommended method for adding 7+ lights.

### Manual Addition

If you know the light ID:

1. Go to **Lights tab**
2. Click **➕ Add Light**
3. Enter:
   - **Light ID**: Numeric ID (1-255)
   - **Name**: Friendly name (e.g., "Kitchen Ceiling")
   - **Controller**: Preferred ESP32 controller
4. Click **Save**

### Finding Light IDs Manually

```bash
adb logcat -c
# Control the light in BRMesh app
adb logcat -d | grep "payload:"
# Look for: 220a00... (0x0a = light ID 10)
```

---

## Creating Scenes

Scenes save lighting states for instant recall.

### Via Web UI

1. Go to **Scenes tab**
2. Click **🎬 Create Scene**
3. Enter **Scene Name** (e.g., "Movie Night")
4. Select lights to include
5. Set each light's:
   - **Color** (RGB picker)
   - **Brightness** (0-255)
   - **Power** (On/Off)
6. Click **Save Scene**

### Activating Scenes

- **Web UI**: Click scene name on Scenes tab
- **Home Assistant**: Call `scene.turn_on` service with scene name
- **Automation**: Use as action in automations

**Example Scenes**:
- "All Off" - Turn everything off
- "Morning" - Warm white, 50% brightness
- "Party" - Rainbow colors, full brightness
- "Night Light" - Dim red, 10% brightness

---

## Managing Controllers

Controllers are ESP32 devices that send BLE commands to lights.

### Adding a Controller

1. Go to **Controllers tab**
2. Click **➕ Add Controller**
3. Enter:
   - **Name**: e.g., "Living Room ESP32"
   - **IP Address**: e.g., `10.1.10.154`
   - **MAC Address**: ESP32 Bluetooth MAC
   - **Location**: Physical location (optional)
   - **Coordinates**: Lat/Lon for map placement
4. Click **Save**

### Generating ESPHome Config

1. Go to **Controllers tab**
2. Click **⬇️ Download Config** next to controller name
3. Save YAML file
4. Copy to `/config/esphome/` in Home Assistant
5. Compile and flash to ESP32

The generated config includes:
- WiFi credentials
- API encryption key
- All assigned lights
- BRMesh fastcon component

**Home Assistant is the source of truth** - update lights in HA, regenerate config, reflash ESP32!

### Signal Strength Matrix

The Controllers tab shows signal strength from each controller to each light:

- 🟢 **Excellent** (-60 dBm or better)
- 🟡 **Good** (-70 to -60 dBm)
- 🟠 **Fair** (-80 to -70 dBm)
- 🔴 **Poor** (below -80 dBm)

Use this to optimize controller placement and light assignments.

---

## Best Practices

### Initial Setup Checklist

- [ ] Set mesh key in Settings
- [ ] Verify MQTT connection (check HA integration)
- [ ] Set property coordinates for map view
- [ ] Enable BLE discovery
- [ ] Add first controller
- [ ] Scan for existing lights
- [ ] Test light control
- [ ] Create first scene

### Adding Multiple Lights

1. **Power on all new lights at once** (pairing mode)
2. Click **Scan for Lights** once
3. Wait for full scan (30-60 seconds)
4. All lights register automatically
5. Rename them in batch using GUI

**Pro tip**: Use sequential naming (Living Room 1, Living Room 2, etc.) for easy organization.

### Backup Strategy

1. Export configuration monthly
2. Save exported JSON to version control
3. Test restore process once
4. Keep copy outside Home Assistant

### Performance Tips

- **Limit scan duration** to 30 seconds for 5-10 lights
- **Assign lights to nearest controller** for best signal
- **Use map view** to visualize coverage gaps
- **Monitor signal strength** and adjust placement

---

## Troubleshooting

### Settings Not Saving

- Check `/data/options.json` permissions
- Verify add-on has write access
- Check logs: Settings → Add-on Logs

### Lights Not Discovered

- Verify light is in pairing mode (rapid blinking)
- Check ESP32 Bluetooth is active
- Ensure BLE discovery is enabled in Settings
- Try manual addition with known light ID

### Map Not Loading

- Verify coordinates are correct (latitude/longitude)
- Check internet connection (ESRI tiles require internet)
- Try different zoom level
- Clear browser cache

### MQTT Connection Failed

- If using HA's service: Verify Mosquitto add-on is running
- If using external broker: Check host/port/credentials
- Check MQTT integration in HA
- Review add-on logs for connection errors

### NSPanel Not Responding

- Verify NSPanel entity ID is correct
- Check MQTT topics are matching
- Ensure NSPanel firmware is up to date
- Test with manual MQTT publish

---

## FAQ

**Q: Do I need to edit any YAML files?**
A: No! Everything is configurable through the web UI.

**Q: Can I add lights without the Android app?**
A: Yes! Use BLE discovery to add lights phone-free.

**Q: How many lights can I manage?**
A: Up to 255 lights per mesh network.

**Q: How many controllers do I need?**
A: One ESP32 can cover ~1500 sq ft. Add more for larger properties.

**Q: Can I use existing ESPHome configs?**
A: Yes, but GUI-generated configs are recommended as HA becomes source of truth.

**Q: Do settings persist after add-on restart?**
A: Yes, all settings are saved to persistent storage.

**Q: Can I control lights when internet is down?**
A: Yes! Everything runs locally - internet only needed for map tiles.

---

## Next Steps

1. **Complete initial setup** using Settings tab
2. **Add all your lights** using BLE discovery
3. **Create useful scenes** (All Off, Movie Night, etc.)
4. **Set up automations** in Home Assistant
5. **Generate ESPHome configs** for controllers
6. **Optimize placement** using signal strength matrix

**You're ready to go!** No more manual YAML editing, no more app dependency - just pure GUI-powered smart lighting control.

For detailed feature documentation, see [NEW_FEATURES.md](NEW_FEATURES.md).
For quick setup instructions, see [QUICK_START.md](QUICK_START.md).

---

## Credits

This add-on wouldn't be possible without:

**[@scross01](https://github.com/scross01)** - Creator and maintainer of [esphome-fastcon](https://github.com/scross01/esphome-fastcon), the ESPHome component that handles BRMesh/Fastcon BLE protocol communication. Your work made this entire project possible! 🙏

Additional thanks to:
- **[Mooody](https://mooody.me/)** - Original Fastcon BLE protocol documentation
- **[ArcadeMachinist](https://github.com/ArcadeMachinist)** - brMeshMQTT reference implementation
- **Home Assistant Community** - Testing, feedback, and support
