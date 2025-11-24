# BRMesh Bridge - Complete Setup & Usage Guide

## 🎯 Quick Start

Your BRMesh Bridge add-on is ready to deploy! This guide covers everything from installation to advanced usage.

## 📦 What's Included

The add-on provides:
- **Web UI** (Port 8099) - Interactive dashboard for light management
- **MQTT Integration** - Full Home Assistant auto-discovery
- **Effects Engine** - 8 pre-built lighting effects
- **Map View** - Place lights on satellite imagery
- **Multi-Controller Support** - Scale to 11+ lights with multiple ESP32s

## 🚀 Installation Steps

### 1. Deploy the Add-on

The add-on files are located at:
```
/addons/ha-brmesh-bridge/
```

**Files Created:**
- `config.yaml` - Add-on manifest
- `Dockerfile` - Container image
- `brmesh_bridge.py` - Main bridge logic
- `effects.py` - Effects engine
- `web_ui.py` - Flask web application
- `run.sh` - Startup script
- `templates/index.html` - Web UI
- `static/css/style.css` - Styling
- `static/js/app.js` - Frontend JavaScript

### 2. Configure the Add-on

Edit `/data/options.json` (or use Home Assistant UI):

```json
{
  "mesh_key": "30323336",
  "mqtt_host": "core-mosquitto",
  "mqtt_port": 1883,
  "mqtt_user": "",
  "mqtt_password": "",
  
  "lights": [
    {
      "light_id": 10,
      "name": "Melpo Light - Front Porch",
      "color_interlock": true,
      "location": {
        "x": null,
        "y": null
      },
      "preferred_controller": "esp32_01"
    }
  ],
  
  "controllers": [
    {
      "name": "esp32_01",
      "ip": "10.1.10.154",
      "mac": "AA:BB:CC:DD:EE:FF",
      "location": {
        "x": null,
        "y": null
      }
    }
  ],
  
  "map_enabled": true,
  "map_latitude": 37.7749,
  "map_longitude": -122.4194,
  "map_zoom": 19,
  
  "scenes": [
    {
      "name": "Christmas",
      "effect": "christmas",
      "light_ids": [10],
      "params": {
        "interval": 1.0
      }
    }
  ]
}
```

### 3. Start the Add-on

```bash
# From Home Assistant:
Supervisor → BRMesh Bridge → Start
```

### 4. Access Web UI

Open: `http://homeassistant.local:8099`

## 🔧 Configuration Details

### Discovering Light IDs

You already know light ID 10 works. To find more:

```powershell
# Connect Android device
adb logcat -c

# Control a light in the BRMesh app

# Check payload
adb logcat -d | Select-String 'payload:'
```

Example output: `payload: 220a00...` → Light ID = 0x0a = **10**

### Adding More Lights

Once you discover more light IDs:

1. Add to `options.json`:
```json
{
  "light_id": 11,
  "name": "Back Yard Light",
  "color_interlock": true,
  "location": {"x": null, "y": null},
  "preferred_controller": "esp32_01"
}
```

2. Restart add-on
3. Light appears in Home Assistant automatically!

### ESP32 Controller Setup

You already have ESP32 at **10.1.10.154** running ESPHome with the fastcon component.

**Current `brmesh-controller.yaml`:**
```yaml
esphome:
  name: brmesh-controller

esp32:
  board: esp32dev
  framework:
    type: arduino

wifi:
  ssid: "IoT"
  password: !secret wifi_password

api:
  encryption:
    key: !secret api_encryption_key

ota:
  password: !secret ota_password

logger:

external_components:
  - source: github://scross01/esphome-fastcon@dev
    components: [fastcon]

esp32_ble_server:

fastcon:
  mesh_key: "30323336"

light:
  - platform: fastcon
    id: brmesh_light_10
    name: "BRMesh Light 10"
    light_id: 10
    color_interlock: true
```

**To add more lights to ESP32** (optional - or use MQTT bridge):
```yaml
light:
  - platform: fastcon
    id: brmesh_light_10
    name: "BRMesh Light 10"
    light_id: 10
    color_interlock: true
  
  - platform: fastcon
    id: brmesh_light_11
    name: "BRMesh Light 11"
    light_id: 11
    color_interlock: true
```

## 🗺️ Map View Setup

### 1. Get Your Property Coordinates

Visit: https://www.google.com/maps
- Find your property
- Right-click → "What's here?"
- Copy coordinates (e.g., `37.7749, -122.4194`)

### 2. Update Configuration

```json
{
  "map_enabled": true,
  "map_latitude": 37.7749,
  "map_longitude": -122.4194,
  "map_zoom": 19
}
```

### 3. Place Lights on Map

1. Open Web UI → Map View tab
2. Drag light markers to physical locations
3. Click "💾 Save Layout"

### 4. (Optional) Use Google Satellite Imagery

Edit `static/js/app.js` line 330:

```javascript
// Replace OpenStreetMap with Google Satellite
L.tileLayer('https://mt1.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
    maxZoom: 20,
    attribution: '© Google'
}).addTo(map);
```

## ✨ Using Effects

### From Web UI

1. Go to Effects tab
2. Select lights (checkboxes)
3. Click effect card (e.g., "RAINBOW")
4. Effect starts immediately

### From Home Assistant

Create automation:

```yaml
automation:
  - alias: "Start Christmas Effect at Sunset"
    trigger:
      platform: sun
      event: sunset
    action:
      service: rest_command.brmesh_effect
      data:
        effect: "christmas"
        lights: "10,11,12"
```

Add to `configuration.yaml`:

```yaml
rest_command:
  brmesh_effect:
    url: "http://localhost:8099/api/effects/{{ effect }}"
    method: POST
    payload: '{"light_ids": [{{ lights }}], "params": {}}'
    content_type: 'application/json'
```

### Available Effects

| Effect | Description | Parameters |
|--------|-------------|------------|
| `rainbow` | Color spectrum cycle | `speed`, `brightness` |
| `color_loop` | Custom color cycle | `colors`, `interval` |
| `twinkle` | Random twinkling | `color`, `speed` |
| `fire` | Flickering fire | `intensity` |
| `christmas` | Red/green alternating | `interval` |
| `halloween` | Orange/purple spooky | `interval` |
| `strobe` | Fast flash | `color`, `frequency` |
| `breathe` | Smooth pulsing | `color`, `speed` |

## 🎬 Scene Management

### Creating Scenes

**Method 1: Configuration**

```json
{
  "scenes": [
    {
      "name": "Movie Night",
      "lights": [
        {"light_id": 10, "rgb": [50, 0, 100], "brightness": 80, "state": true},
        {"light_id": 11, "rgb": [50, 0, 100], "brightness": 80, "state": true}
      ]
    }
  ]
}
```

**Method 2: Web UI**

1. Set lights to desired states manually
2. Click "➕ Create New Scene"
3. Name it and save

### Applying Scenes

**Web UI:** Scenes tab → Click scene card

**Home Assistant:**
```yaml
automation:
  - alias: "Movie Night Scene"
    trigger:
      platform: time
      at: "20:00:00"
    action:
      service: rest_command.brmesh_scene
      data:
        scene: "Movie Night"
```

```yaml
# configuration.yaml
rest_command:
  brmesh_scene:
    url: "http://localhost:8099/api/scenes/{{ scene }}"
    method: POST
```

## 📡 Multi-Controller Setup (For 11+ Lights)

### When to Add More ESP32s

- Coverage area > 50 feet
- Signal strength < -70 dBm
- Some lights not responding reliably

### Adding a Second ESP32

1. **Flash new ESP32** with modified config:

```yaml
esphome:
  name: brmesh-controller-02  # Different name!

# ... same wifi, api, ota ...

fastcon:
  mesh_key: "30323336"  # SAME mesh key!

light:
  - platform: fastcon
    id: brmesh_light_11
    name: "BRMesh Light 11"
    light_id: 11
    color_interlock: true
```

2. **Add to configuration:**

```json
{
  "controllers": [
    {
      "name": "esp32_01",
      "ip": "10.1.10.154",
      "mac": "AA:BB:CC:DD:EE:FF",
      "location": {"x": -122.4194, "y": 37.7749}
    },
    {
      "name": "esp32_02",
      "ip": "10.1.10.155",
      "mac": "BB:CC:DD:EE:FF:00",
      "location": {"x": -122.4195, "y": 37.7750}
    }
  ]
}
```

3. **Assign lights to controllers:**

```json
{
  "lights": [
    {"light_id": 10, "preferred_controller": "esp32_01"},
    {"light_id": 11, "preferred_controller": "esp32_02"}
  ]
}
```

### Signal Strength Optimization

1. Open Web UI → Controllers tab
2. View "Signal Strength Matrix"
3. Green = strong (-60 dBm or better)
4. Orange = medium (-70 to -60 dBm)
5. Red = weak (< -70 dBm)

Move ESP32s to maximize green indicators.

## 🔍 Troubleshooting

### Lights Not Responding

**Check ESP32 Status:**
```
Web UI → Controllers tab
```

Should show "Online" with green indicator.

**Verify Mesh Key:**
```powershell
adb logcat -d | Select-String "jyq_helper.*key"
```

Must match your configuration.

**Check Light ID:**
```powershell
adb logcat -c
# Control light in app
adb logcat -d | Select-String 'payload:'
```

Second byte (hex) = light ID.

### Web UI Not Loading

1. Check add-on logs:
```
Supervisor → BRMesh Bridge → Logs
```

2. Should see:
```
Web UI available at http://localhost:8099
```

3. Verify port 8099 accessible:
```powershell
Test-NetConnection -ComputerName homeassistant.local -Port 8099
```

### MQTT Issues

**Check broker:**
```
Supervisor → Mosquitto broker → Logs
```

**Test connection:**
```powershell
# From another machine
mosquitto_sub -h homeassistant.local -t 'homeassistant/light/brmesh_10/#' -v
```

Should see discovery messages.

### Effect Not Starting

**Check light selection:**
- Effects tab → at least one light checkbox selected

**Check logs:**
```
Supervisor → BRMesh Bridge → Logs
```

Look for:
```
INFO: Starting effect rainbow for lights [10]
```

## 📊 API Reference

All endpoints accept/return JSON.

### Lights

**GET /api/lights**
```json
[
  {
    "id": 10,
    "name": "Melpo Light",
    "state": {"state": true, "brightness": 255, "rgb": [255, 255, 255]},
    "location": {"x": -122.4194, "y": 37.7749},
    "signal_strength": {}
  }
]
```

**POST /api/lights/{id}**
```json
{
  "state": true,
  "brightness": 200,
  "rgb": [255, 0, 0]
}
```

**POST /api/lights/{id}/location**
```json
{
  "x": -122.4194,
  "y": 37.7749
}
```

### Effects

**GET /api/effects**
```json
[
  {"name": "rainbow", "params": ["speed", "brightness"]},
  {"name": "christmas", "params": ["interval"]}
]
```

**POST /api/effects/{name}**
```json
{
  "light_ids": [10, 11],
  "params": {
    "speed": 1.0,
    "brightness": 255
  }
}
```

**POST /api/effects/stop**
```json
{
  "effect_id": "rainbow_10-11"
}
```

### Scenes

**GET /api/scenes**
```json
[
  {
    "name": "Christmas",
    "effect": "christmas",
    "light_ids": [10, 11],
    "params": {"interval": 1.0}
  }
]
```

**POST /api/scenes/{name}**
```
(No body required)
```

### Controllers

**GET /api/controllers**
```json
[
  {
    "name": "esp32_01",
    "ip": "10.1.10.154",
    "mac": "AA:BB:CC:DD:EE:FF",
    "location": {"x": -122.4194, "y": 37.7749}
  }
]
```

## 🎓 Next Steps

### 1. Add All Your Lights

Use ADB to discover all 11 light IDs and add them to configuration.

### 2. Map Your Property

Place all lights on the satellite map view.

### 3. Create Custom Scenes

- "Welcome Home" - warm white entrance lights
- "Security Mode" - bright white all lights
- "Party Mode" - rainbow effect
- "Bedtime" - dim warm lights

### 4. Set Up Automations

- Sunset → Turn on outdoor lights
- Motion sensor → Activate scene
- Time-based schedules
- Weather-triggered lighting

### 5. Optimize Coverage

- Monitor signal strength
- Add ESP32 controllers as needed
- Document working ranges

## 📞 Support

- **GitHub Issues:** Report bugs or request features
- **Home Assistant Forum:** Community support
- **Documentation:** This guide

## 🎉 You're Ready!

Your BRMesh Bridge is fully configured and ready to deploy. Start by:

1. Accessing the Web UI: `http://homeassistant.local:8099`
2. Adding your 11 lights to the configuration
3. Creating your first custom scene
4. Setting up a sunset automation

Enjoy your smart lighting system! 💡✨
