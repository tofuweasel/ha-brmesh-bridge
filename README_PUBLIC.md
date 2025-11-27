# BRMesh Bridge Pro for Home Assistant

[![GitHub Release](https://img.shields.io/github/release/YOUR_USERNAME/ha-brmesh-bridge.svg)](https://github.com/YOUR_USERNAME/ha-brmesh-bridge/releases)
[![License](https://img.shields.io/github/license/YOUR_USERNAME/ha-brmesh-bridge.svg)](LICENSE)
[![HACS](https://img.shields.io/badge/HACS-Custom-orange.svg)](https://github.com/hacs/integration)

Bridge your BRMesh/Fastcon BLE lights to Home Assistant with **complete GUI configuration**, phone-free operation, and advanced features.

## ✨ Features

- 🎨 **Web UI Configuration** - No manual file editing required!
- 🗺️ **Map View** - Visualize lights on satellite imagery (ESRI ArcGIS)
- 🔍 **BLE Discovery** - Add lights without phone or app
- 📱 **App Sync** - Import device names from BRMesh Android app
- 🎭 **8 Built-in Effects** - Rainbow, fire, twinkle, and more
- 🎬 **Scene Management** - Create and activate multi-light scenes
- 📟 **NSPanel Integration** - Optional Nextion touch display
- 🔧 **ESPHome Generator** - Auto-generate controller configs
- 📡 **MQTT Discovery** - Automatic Home Assistant entities
- 🔌 **Multi-Controller** - Support multiple ESP32s with signal monitoring
- 📍 **Auto-Location** - Detects your Home Assistant location automatically

## 🚀 Quick Start

### Installation

1. Go to **Settings** → **Add-ons** → **Add-on Store**
2. Click ⋮ (three dots) → **Repositories**
3. Add: `https://github.com/tofuweasel/ha-brmesh-bridge`
4. Search for "BRMesh Bridge"
5. Click **Install**
6. Start the add-on

### Configuration (GUI-Based!)

1. Start the add-on
2. Open Web UI
3. Go to Settings tab
4. Enter your mesh key
5. Click "Scan for Lights"
6. Done! ✨

See [QUICK_START.md](QUICK_START.md) for detailed 5-minute setup guide.

## 📖 Documentation

- **[QUICK_START.md](QUICK_START.md)** - 5-minute setup guide
- **[GUI_CONFIGURATION.md](GUI_CONFIGURATION.md)** - Complete GUI configuration guide
- **[NEW_FEATURES.md](NEW_FEATURES.md)** - Detailed feature documentation
- **[SETUP_GUIDE.md](SETUP_GUIDE.md)** - Comprehensive setup instructions
- **[DEPLOYMENT.md](DEPLOYMENT.md)** - Self-hosting and deployment guide

## 🎯 Use Cases

- **Outdoor Lighting** - Control garden, patio, and driveway lights
- **Holiday Displays** - Christmas, Halloween, and custom scenes
- **Security Lighting** - Motion-triggered perimeter lighting
- **Ambiance Control** - Dynamic color effects for entertainment
- **Multi-Property** - Manage lights across multiple buildings

## 🛠️ Requirements

- Home Assistant OS or Supervised
- ESP32 device (any variant)
- BRMesh/Fastcon BLE lights
- MQTT broker (Mosquitto add-on recommended)

## 💡 Supported Lights

Any light compatible with:
- **BRMesh app** (Broadlink mesh protocol)
- **Fastcon app** (Fastcon BLE protocol)

Common brands:
- Melpo
- Generic Broadlink-compatible bulbs
- Most cheap RGB+W BLE bulbs from AliExpress/Amazon

⚠️ **Not compatible** with brLight app (different protocol)

## 📱 Phone-Free Operation

Set up lights without ever touching the Android app:

1. Power on light (it blinks)
2. Click "Scan for Lights" in Web UI
3. Light discovered and configured
4. Control via Home Assistant!

Perfect for adding multiple lights without manual pairing!

## 🗺️ Map View

Visualize your lighting layout on satellite imagery:

- Auto-detects Home Assistant location
- Drag-drop light placement
- Signal strength visualization
- Controller coverage display
- ESRI ArcGIS satellite tiles (free, no API key)

## 🎭 Effects Engine

8 built-in lighting effects:

1. **Rainbow** - Smooth color cycling
2. **Color Loop** - Sequential color changes
3. **Twinkle** - Random sparkle effect
4. **Fire** - Flickering flame simulation
5. **Christmas** - Red/green alternating
6. **Halloween** - Orange/purple spooky
7. **Strobe** - Fast flashing
8. **Breathe** - Gentle pulsing

Apply to individual lights or groups, adjust speed and intensity.

## 🔧 ESPHome Integration

Generate ESPHome configs directly from Home Assistant:

1. Configure lights in GUI
2. Click "Download Config"
3. Flash to ESP32
4. Home Assistant is the source of truth!

Supports multiple controllers with automatic light assignment.

## 🙏 Credits

This add-on wouldn't be possible without:

**[@scross01](https://github.com/scross01)** - Creator and maintainer of [esphome-fastcon](https://github.com/scross01/esphome-fastcon), the ESPHome component that makes BRMesh/Fastcon BLE control possible. **Thank you for making this project a reality!** 🙏

Additional acknowledgments:
- **[Mooody](https://mooody.me/)** - Original Fastcon BLE protocol analysis
- **[ArcadeMachinist](https://github.com/ArcadeMachinist)** - brMeshMQTT implementation reference
- **[Home Assistant Community](https://community.home-assistant.io/t/brmesh-app-bluetooth-lights/473486)** - Testing, feedback, and support

## 🐛 Support

**Add-on Issues**: [Create an issue](https://github.com/YOUR_USERNAME/ha-brmesh-bridge/issues)

**ESPHome Component**: Visit [esphome-fastcon](https://github.com/scross01/esphome-fastcon)

**Community**: [Home Assistant Community Thread](https://community.home-assistant.io/t/brmesh-app-bluetooth-lights/473486)

## 📋 Changelog

### v0.9.0 (November 2025)

**Beta Release: GUI Configuration**

- ✅ Complete web-based configuration - no manual file editing!
- ✅ Auto-detect Home Assistant location for maps
- ✅ BLE discovery for phone-free light addition
- ✅ Import/export configuration
- ✅ 8 built-in lighting effects
- ✅ Scene management
- ✅ NSPanel integration
- ✅ Multi-controller support

See [CHANGELOG.md](CHANGELOG.md) for full version history.

## 📜 License

MIT License - See [LICENSE](LICENSE) file for details.

## 🌟 Star This Repo!

If this add-on helps you, please ⭐ star this repository to show support!

## 🔗 Links

- **Repository**: https://github.com/tofuweasel/ha-brmesh-bridge
- **Issues**: https://github.com/tofuweasel/ha-brmesh-bridge/issues
- **ESPHome Component**: https://github.com/scross01/esphome-fastcon
- **Home Assistant**: https://www.home-assistant.io/
- **HACS**: https://hacs.xyz/

---

Made with ❤️ for the Home Assistant community
