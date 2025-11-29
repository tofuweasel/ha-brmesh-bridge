# ESP32 Setup Guide for BRMesh Bridge

## Overview
The ESP BLE Bridge requires an ESP32 flashed with ESPHome firmware to scan for and control BRMesh lights via Bluetooth.

## Prerequisites
- ESP32 development board (ESP32-DevKitC or similar)
- USB cable for flashing
- BRMesh/Fastcon lights in pairing mode

## Setup Steps

### 1. Add Controller in Web UI
1. Open the Web UI at `http://homeassistant.local:8099`
2. Go to **Controllers** tab
3. Click **Add Controller**
4. Enter a name (e.g., `esp-ble-bridge`)
5. Click **Save**

The system will automatically generate an ESPHome configuration file at:
```
/config/esphome/esp-ble-bridge.yaml
```

### 2. Flash ESP32 with ESPHome Firmware

#### Option A: Flash via Web UI (Recommended)
1. Connect ESP32 to Home Assistant host via USB
2. In Web UI, go to **Controllers** tab
3. Click **Build & Flash** for your controller
4. Select the USB port where ESP32 is connected
5. Wait for compilation and flashing (5-10 minutes)

#### Option B: Flash using ESPHome CLI
```bash
# From Home Assistant terminal
cd /config/esphome
esphome run esp-ble-bridge.yaml
```

#### Option C: Flash using ESPHome Dashboard
1. Open ESPHome dashboard in Home Assistant
2. Click **Install** on your controller
3. Choose **Plug into this computer**
4. Select serial port and flash

### 3. Verify ESP32 is Online
After flashing, the ESP32 should:
- Connect to your WiFi network
- Be discoverable as `esp-ble-bridge.local`
- Show up in ESPHome dashboard as "Online"

**Test connection:**
```bash
ping esp-ble-bridge.local
```

Or check the web interface:
```
http://esp-ble-bridge.local/
```

### 4. Pair Lights

Once ESP32 is online and running:

1. **Factory reset your BRMesh light:**
   - Turn on the light
   - Toggle power 5 times (on/off/on/off/on)
   - Light should flash to indicate pairing mode

2. **Start pairing in Web UI:**
   - Go to **Lights** tab
   - Click **Pair New Light**
   - Wait for scan (30 seconds)
   - Found lights will appear in the list

3. **Configure the light:**
   - Set a friendly name
   - Choose device type (RGB, RGBW, etc.)
   - Set location (optional)
   - Click **Save**

## Troubleshooting

### ESP32 Not Found
**Symptoms:** `Cannot resolve esp-ble-bridge.local`

**Solutions:**
- Check ESP32 is powered on
- Verify WiFi credentials in `/config/secrets.yaml`
- Check router for DHCP lease
- Try IP address instead of `.local` hostname
- Reboot ESP32

### Connection Errors During Scan
**Symptoms:** `Connection aborted`, `Remote end closed connection`

**Solutions:**
- Verify ESP32 firmware is flashed correctly
- Check web server is enabled in ESPHome config
- Ensure ESP32 has stable WiFi connection
- Check ESP32 logs in ESPHome dashboard for errors
- Try re-flashing the ESP32

### No Lights Found During Scan
**Symptoms:** `Found 0 BRMesh devices`

**Solutions:**
- Ensure lights are in pairing mode (factory reset)
- Move lights closer to ESP32 (BLE has limited range)
- Check ESP32 logs show BLE scanner is working
- Verify lights are BRMesh/Fastcon compatible
- Try scanning for longer duration (60+ seconds)

### ESP32 Keeps Rebooting
**Symptoms:** Frequent disconnections, unstable connection

**Solutions:**
- Check power supply (use quality USB cable/adapter)
- Reduce BLE scan activity in ESPHome config
- Check for overheating
- Flash stable ESPHome version
- Try different ESP32 board

## Configuration Files

### secrets.yaml
Located at `/config/secrets.yaml`, should contain:
```yaml
wifi_ssid: "YourWiFiNetwork"
wifi_password: "YourWiFiPassword"
mesh_key: "b9d0ea08"  # Your BRMesh network key
api_encryption_key: "base64-encoded-key"
ota_password: "your-ota-password"
```

### Generated ESPHome Config
Located at `/config/esphome/esp-ble-bridge.yaml`

Key components:
- **esp32_ble_tracker**: Scans for BLE devices
- **fastcon component**: Controls BRMesh lights
- **web_server**: Provides web interface
- **api**: ESPHome native API for Home Assistant
- **mqtt**: Communication with bridge addon

## Advanced Configuration

### Multiple ESP32 Controllers
For large homes, you can add multiple ESP32 controllers:
1. Add each controller in Web UI with unique name
2. Flash each ESP32 with its own config
3. All controllers share the same mesh key
4. Controllers automatically coordinate via MQTT

### Custom BLE Scan Settings
Edit ESPHome config to adjust scan parameters:
```yaml
esp32_ble_tracker:
  scan_parameters:
    interval: 320ms  # How often to scan
    window: 300ms    # Scan duration
    active: true     # Send scan requests
    continuous: true # Keep scanning
```

### Static IP Configuration
Add to controller in Web UI or edit ESPHome config:
```yaml
wifi:
  manual_ip:
    static_ip: 10.1.10.154
    gateway: 10.1.10.1
    subnet: 255.255.255.0
```

### Manual Configuration & Updates
The addon will **never automatically overwrite** your existing ESPHome configuration files on startup.

- **To apply changes:** You must click the **Regenerate YAML** button in the Web UI after adding lights or changing settings.
- **To prevent ANY overwrites:** Add `# manual_config: true` to the top of your YAML file. This protects it even from the Regenerate button.

```yaml
# manual_config: true
```

## Next Steps
- [Pairing Guide](PAIRING_GUIDE.md) - Detailed pairing process
- [Protocol Documentation](BRMESH_PROTOCOL_COMPLETE.md) - Technical details
- [Quick Reference](QUICK_REFERENCE.md) - Command reference
