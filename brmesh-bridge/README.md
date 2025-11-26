# BRMesh Bridge Add-on

Bridge your BRMesh lights to Home Assistant with dynamic light management.

## Features

- **🎨 Web UI Configuration**: Complete GUI-based configuration - no manual file editing required!
- **🗺️ Map View**: Visualize and place lights on satellite imagery (ESRI ArcGIS)
- **🔍 BLE Discovery**: Automatically discover and add new lights without phone
- **📱 App Sync**: Import device names from BRMesh Android app via ADB
- **🎭 Effects Engine**: 8 built-in lighting effects (rainbow, fire, twinkle, etc.)
- **🎬 Scene Management**: Create and activate multi-light scenes
- **📟 NSPanel Integration**: Optional Nextion touch display support
- **🔧 ESPHome Generator**: Auto-generate controller configs from Home Assistant settings
- **📡 MQTT Discovery**: Automatically creates Home Assistant entities
- **🔌 Multiple Controllers**: Support for multiple ESP32 controllers with signal strength monitoring
- **🚫 Phone-Free Operation**: Set up 7+ new lights without ever touching the Android app
- **🔄 Reset & Recovery**: Factory reset lights, remove devices, reset controllers, or full system reset

## Configuration

### Quick Start (GUI-Based)

1. **Install this add-on** from the Add-on Store
2. **Start the add-on** and open the Web UI
3. **Go to Settings tab** in the web interface
4. **Configure your mesh key** (extract using `adb logcat` if needed)
5. **Set up MQTT** (defaults to Home Assistant's service automatically)
6. **Set map coordinates** for your property (optional)
7. **Power on new lights** and click "Scan for Lights"
8. **Save settings** - that's it!

No manual YAML editing required! Everything is configurable through the intuitive web interface.

### Advanced Setup (Manual)

### Example Configuration

```yaml
mesh_key: "YOUR_MESH_KEY"  # 8 hex characters from ADB logcat
mqtt_host: "core-mosquitto"
mqtt_port: 1883
mqtt_user: ""
mqtt_password: ""
discovery_enabled: true
lights:
  - light_id: 10
    name: "Melpo Light"
    color_interlock: true
    supports_cwww: false
  - light_id: 11
    name: "Kitchen Light"
    color_interlock: true
    supports_cwww: false
```

### Adding New Lights

1. Pair the light in the BRMesh app
2. Control it once to capture the light ID via logcat
3. Add it to the `lights` configuration above
4. Restart the add-on
5. The light appears automatically in Home Assistant!

## Finding Light IDs

Use ADB to capture light IDs:

```bash
adb logcat -c
# Control the light in the BRMesh app
adb logcat -d | grep "payload:"
```

Look for the second byte in the payload - that's your light ID in hex.
Example: `220a00...` means light ID 10 (0x0a = 10 decimal)

## Reset & Recovery

The add-on includes comprehensive reset functionality:

- **Factory Reset Light**: Clear pairing data and return light to pairing mode
- **Remove Light**: Remove light from Home Assistant without factory reset
- **Reset Controller**: Remove ESP32 controller from configuration
- **Full System Reset**: Remove all lights, controllers, scenes, and effects

See [RESET_GUIDE.md](RESET_GUIDE.md) for complete documentation.

## Requirements

- ESP32 device running this add-on's bridge code
- BRMesh lights paired in the official app
- MQTT broker (Mosquitto add-on recommended)
- USB or Bluetooth access to ESP32

## Credits

This add-on wouldn't be possible without the incredible work of:

**[@scross01](https://github.com/scross01)** - For developing and maintaining the [esphome-fastcon](https://github.com/scross01/esphome-fastcon) component that makes ESPHome control of BRMesh/Fastcon BLE lights possible. This component does the heavy lifting of BLE communication and protocol implementation. Thank you for your continued development and support! 🙏

Additional acknowledgments:
- **[Mooody](https://mooody.me/)** - Original Fastcon BLE protocol reverse engineering
- **[ArcadeMachinist](https://github.com/ArcadeMachinist)** - brMeshMQTT implementation reference
- **[Home Assistant Community](https://community.home-assistant.io/t/brmesh-app-bluetooth-lights/473486)** - Testing, feedback, and support

## Support

For add-on issues: Create an issue in this repository

For ESPHome component issues: Visit https://github.com/scross01/esphome-fastcon
