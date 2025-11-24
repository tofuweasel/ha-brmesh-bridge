# BRMesh Bridge Pro v2.0 - Quick Start

## 🚀 Setup Your 7 New Lights in 5 Minutes (GUI-Based - No File Editing!)

### Prerequisites
- ✅ ESP32 device (already flashed with ESPHome)
- ✅ Mesh key extracted from BRMesh app (see below)
- ✅ Add-on installed

### Step 1: Open Web UI (10 seconds)

1. Start the BRMesh Bridge add-on
2. Click **"Open Web UI"**
3. Navigate to **⚙️ Settings tab**

### Step 2: Configure Core Settings (30 seconds)

In the Settings tab:

1. **Mesh Key**: Enter your 8-character hex mesh key (extract using ADB - see below)
2. **MQTT Configuration**: Leave "Use Home Assistant's MQTT service" ✅ checked
3. **Map Configuration** (optional):
   - Enter your property latitude/longitude
   - Set zoom level to 18
4. **Feature Toggles**: Ensure these are enabled:
   - ✅ MQTT Auto-Discovery
   - ✅ Auto-generate ESPHome Configurations
   - ✅ BLE Device Discovery
5. Click **💾 Save Settings**

**No manual file editing required!**

### Step 3: Add Your Controller (30 seconds)

1. Go to **Controllers tab**
2. Click **➕ Add Controller**
3. Enter:
   - Name: `Living Room ESP32`
   - IP: `192.168.1.100` (your ESP32's IP address)
   - MAC: Your ESP32's Bluetooth MAC (e.g., `AA:BB:CC:DD:EE:FF`)
   - Location: `Living Room` (optional)
4. Click **Save**

### Step 4: Power On New Lights (1 minute)

1. Plug in all 7 new lights
2. Press button on each until it blinks rapidly (pairing mode)
3. Wait 30 seconds for them to stabilize

### Step 5: Discover Lights Automatically (30 seconds)

1. Go to **Lights tab** in Web UI
2. Click **🔍 Scan for Lights** button
3. Wait 30 seconds while scan runs
4. **All 7 lights appear automatically!**
5. Each gets assigned light IDs 11-17

**No phone needed! No ADB logcat! Just click and wait!**

### Step 6: Rename Lights (2 minutes)

In the Web UI Lights tab:

1. Click on each light's name
2. Enter friendly name:
   - Light 11 → "Back Yard Left"
   - Light 12 → "Back Yard Right"
   - Light 13 → "Garage"
   - Light 14 → "Driveway"
   - Light 15 → "Front Garden"
   - Light 16 → "Side Gate"
   - Light 17 → "Back Patio"
3. Names save automatically

### Step 7: Verify in Home Assistant (30 seconds)

Check Home Assistant:
```
Settings → Devices & Services → MQTT → BRMesh Bridge
```

You should see **8 lights total**:
- light.brmesh_10 (Melpo Light - Front Porch)
- light.brmesh_11 (Back Yard Left)
- light.brmesh_12 (Back Yard Right)
- light.brmesh_13 (Garage)
- light.brmesh_14 (Driveway)
- light.brmesh_15 (Front Garden)
- light.brmesh_16 (Side Gate)
- light.brmesh_17 (Back Patio)

### Step 8: (Optional) Place Lights on Map (2 minutes)

1. Go to **Map tab** in Web UI
2. Drag each light marker to actual location on satellite imagery
3. Click **💾 Save Layout**
4. Now you have visual reference!

### Step 9: (Optional) Update ESP32 Config (2 minutes)

Generate updated ESPHome config with all 8 lights:

**Via Web UI**:
1. Go to **Controllers tab**
2. Click **⬇️ Download Config** next to "Living Room ESP32"
3. Save file

**Flash ESP32**:
```bash
cd /config/esphome
# Download the generated YAML from Web UI
esphome run controller_name.yaml
```

## ✨ Done!

You now have:
- ✅ 8 total lights (1 original + 7 new)
- ✅ All discovered automatically
- ✅ All in Home Assistant
- ✅ Web UI control
- ✅ Automation ready

## 🎯 Quick Commands

```bash
# Scan for new devices
curl http://homeassistant.local:8099/api/scan -X POST

# List all lights
curl http://homeassistant.local:8099/api/lights

# Control a light
curl http://homeassistant.local:8099/api/lights/11 -X POST \
  -H "Content-Type: application/json" \
  -d '{"state": true, "rgb": [255, 0, 0], "brightness": 255}'

# Start Christmas effect
curl http://homeassistant.local:8099/api/effects/christmas -X POST \
  -H "Content-Type: application/json" \
  -d '{"light_ids": [10,11,12,13,14,15,16,17]}'

# Generate ESPHome configs
curl http://homeassistant.local:8099/api/esphome/generate -X POST
```

## 🆘 Troubleshooting

### Lights Not Discovered

```powershell
# Check logs
docker logs addon_brmesh_bridge

# Manual discovery (if lights already paired)
adb logcat -c
# Control each light in BRMesh app
adb logcat -d | Select-String 'payload:'
```

Then manually add to config:
```json
{
  "lights": [
    {"light_id": 11, "name": "New Light 1"}
  ]
}
```

### ESP32 Not Responding

```powershell
# Check ESP32 is online
ping 10.1.10.154

# Check ESPHome logs
esphome logs brmesh-controller.yaml

# Reflash if needed
esphome run brmesh-controller.yaml
```

## 📚 Full Documentation

- **Setup Guide**: SETUP_GUIDE.md
- **New Features**: NEW_FEATURES.md
- **README**: README.md
- **Web UI**: http://homeassistant.local:8099

## 🎉 Next Steps

1. **Map View** - Place lights on satellite map
2. **Scenes** - Create "Christmas", "Halloween", etc.
3. **Automations** - Sunset triggers, motion sensors
4. **NSPanel** - Touch control (optional)

Enjoy your smart lighting! 💡✨

---

## 🙏 Credits

This add-on is built on top of the amazing work by:

**[@scross01](https://github.com/scross01)** - For creating and maintaining the [esphome-fastcon](https://github.com/scross01/esphome-fastcon) component that makes ESPHome control of BRMesh lights possible. Thank you for making this project a reality!
