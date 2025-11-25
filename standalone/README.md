# BRMesh Bridge Standalone

A standalone desktop application for controlling BRMesh/Fastcon lights **without Home Assistant**!

Perfect for users who:
- Don't use Home Assistant
- Want a better alternative to the BRMesh phone app
- Need local control without cloud services
- Want to manage lights from their desktop

## Features

✨ **All the power of BRMesh Bridge, no Home Assistant required!**

- **GUI Control** - Beautiful web interface for managing lights
- **BLE Discovery** - Find and add lights automatically
- **Effects Engine** - 8 built-in light effects
- **Map View** - Visualize light locations on a map
- **ESP32 Builder** - Compile and flash controllers directly
- **No Cloud** - Everything runs locally on your computer
- **Cross-Platform** - Windows, macOS, Linux

## Installation

### Windows

1. Download `BRMesh-Bridge-Setup.exe` from the [latest release](https://github.com/tofuweasel/ha-brmesh-bridge/releases)
2. Run the installer
3. Launch "BRMesh Bridge" from your Start menu
4. The web interface opens automatically at http://localhost:8099

### macOS

1. Download `BRMesh-Bridge.dmg` from the [latest release](https://github.com/tofuweasel/ha-brmesh-bridge/releases)
2. Open the DMG and drag to Applications
3. Launch "BRMesh Bridge" 
4. The web interface opens automatically at http://localhost:8099

### Linux

```bash
# Download and extract
wget https://github.com/tofuweasel/ha-brmesh-bridge/releases/latest/download/brmesh-bridge-linux.tar.gz
tar -xzf brmesh-bridge-linux.tar.gz
cd brmesh-bridge

# Install Python dependencies
pip3 install -r requirements.txt

# Run
python3 brmesh_bridge_standalone.py
```

## Quick Start

1. **Launch the app** - The web interface opens at http://localhost:8099
2. **Configure mesh key** - Enter your BRMesh mesh key (found in app settings)
3. **Scan for lights** - Click "Scan for Lights" to discover BLE devices
4. **Control your lights** - Click lights to turn on/off, change colors, apply effects

## Adding ESP32 Controllers

Want to extend range beyond Bluetooth? Add ESP32 controllers!

1. Click **Controllers** tab
2. Click **Add Controller**
3. Name it and enter IP address
4. Check **Generate ESPHome Config**
5. Click **Build & Flash**
6. Connect ESP32 via USB and wait for flashing to complete

## Configuration

Settings are stored in `~/.brmesh-bridge/` (or equivalent on your OS).

### Manual Configuration

Edit `~/.brmesh-bridge/config.json`:

```json
{
  "mesh_key": "YOUR_MESH_KEY_HERE",
  "mqtt_host": "localhost",
  "mqtt_port": 1883,
  "lights": [],
  "controllers": []
}
```

## vs Home Assistant Add-on

| Feature | Standalone | Home Assistant Add-on |
|---------|-----------|---------------------|
| Control lights | ✅ | ✅ |
| BLE discovery | ✅ | ✅ |
| Effects engine | ✅ | ✅ |
| ESP32 builder | ✅ | ✅ |
| Map view | ✅ | ✅ |
| MQTT integration | Local only | Full HA integration |
| Automations | ❌ | ✅ (via HA) |
| Voice control | ❌ | ✅ (via HA) |
| Mobile app | Web only | ✅ (HA Companion) |

**Use Standalone if:** You just want to control lights, don't need home automation
**Use HA Add-on if:** You want full smart home integration with automations, voice control, etc.

## Building from Source

```bash
git clone https://github.com/tofuweasel/ha-brmesh-bridge.git
cd ha-brmesh-bridge/standalone

# Install dependencies
pip3 install -r requirements.txt

# Run standalone app
python3 brmesh_bridge_standalone.py
```

## Creating Executables

### Windows
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.ico --name="BRMesh Bridge" brmesh_bridge_standalone.py
```

### macOS
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --icon=icon.icns --name="BRMesh Bridge" brmesh_bridge_standalone.py
```

### Linux
```bash
pip install pyinstaller
pyinstaller --onefile --name="brmesh-bridge" brmesh_bridge_standalone.py
```

## Troubleshooting

### Bluetooth not working
- **Windows**: Install Bluetooth drivers, run as Administrator
- **Linux**: Add user to `bluetooth` group: `sudo usermod -a -G bluetooth $USER`
- **macOS**: Grant Bluetooth permissions in System Preferences

### Can't find lights
1. Make sure Bluetooth is enabled
2. Check that lights are powered on
3. Verify mesh key is correct
4. Try resetting lights (power cycle)

### ESP32 flashing fails
1. Install USB drivers (CP210x or CH340)
2. Check USB cable is data-capable
3. Hold BOOT button while flashing
4. Try a different USB port

## Support

Found a bug? Have a feature request?
[Open an issue on GitHub](https://github.com/tofuweasel/ha-brmesh-bridge/issues)

## License

MIT License - See LICENSE file for details

## Credits

- BRMesh protocol implementation by [@scross01](https://github.com/scross01/esphome-fastcon)
- Icons from [Font Awesome](https://fontawesome.com)
