# ESP32 Connection Issue - Diagnosis and Fix

## The Problem

When attempting to pair lights, you're seeing this error:
```
ERROR:ble_discovery:BLE scan error: ('Connection aborted.', RemoteDisconnected('Remote end closed connection without response'))
```

The BLE discovery is trying to connect to the ESP32 at `10.1.10.154` via HTTP to fetch BLE scan logs, but the connection is being closed/refused.

## Root Cause

**The ESP32 controller has not been flashed with the ESPHome firmware yet.**

The esp-ble-bridge addon generates ESPHome configuration files automatically, but you need to manually flash the ESP32 device with this firmware before it can:
- Scan for BRMesh devices over Bluetooth
- Control lights
- Communicate with the bridge addon

## Solution

### Step 1: Verify Controller Configuration
Your controller `esp-ble-bridge` was added successfully:
```
INFO:web_ui:✅ Controller 'esp-ble-bridge' added successfully with ID: 1
INFO:esphome_generator:Generated ESPHome config: /config/esphome/esp-ble-bridge.yaml
```

This generated the ESPHome configuration at `/config/esphome/esp-ble-bridge.yaml`.

### Step 2: Flash the ESP32

You have several options:

#### Option A: Use the Web UI (Easiest)
1. Open http://homeassistant.local:8099
2. Go to **Controllers** tab
3. Click **Build & Flash** for `esp-ble-bridge`
4. Connect your ESP32 via USB to the Home Assistant machine
5. Select the serial port (e.g., `/dev/ttyUSB0`)
6. Click Flash and wait (takes 5-10 minutes)

#### Option B: Use ESPHome CLI
From Home Assistant terminal:
```bash
cd /config/esphome
esphome run esp-ble-bridge.yaml
```

#### Option C: Use ESPHome Dashboard
1. Open ESPHome dashboard in Home Assistant
2. Find `esp-ble-bridge`
3. Click Install → Plug into this computer
4. Select port and flash

### Step 3: Verify ESP32 is Online

After flashing, check if ESP32 is online:
```bash
ping esp-ble-bridge.local
```

Or visit:
```
http://esp-ble-bridge.local/
```

You should see the ESPHome web interface with logs.

### Step 4: Try Pairing Again

Once the ESP32 is online:
1. Factory reset your BRMesh light (power cycle 5 times)
2. In Web UI, click **Pair New Light**
3. The ESP32 will scan for 30 seconds
4. Found lights will appear in the list

## What Changed

I've improved the error messages in `ble_discovery.py` to provide clearer feedback when the ESP32 is not responding:

### Before
```
ERROR:ble_discovery:BLE scan error: ('Connection aborted.', ...)
```

### After
```
❌ ESP32 CONNECTION FAILED
╔══════════════════════════════════════════════════════════════════════╗
║  Your ESP32 controller needs to be flashed with ESPHome firmware     ║
║  before it can discover lights.                                      ║
║                                                                      ║
║  QUICK FIX:                                                          ║
║  1. Go to Web UI: http://homeassistant.local:8099                   ║
║  2. Controllers tab → Build & Flash                                  ║
║  3. Connect ESP32 via USB and flash                                  ║
║  4. Wait for ESP32 to connect to WiFi                               ║
║  5. Try pairing again                                                ║
╚══════════════════════════════════════════════════════════════════════╝
```

## Files Modified

1. **ble_discovery.py**
   - Added `check_esp32_online()` method to verify connectivity
   - Improved error messages with actionable steps
   - Added retry logic with exponential backoff
   - Better handling of connection failures

2. **ESP32_SETUP_GUIDE.md** (new file)
   - Comprehensive setup documentation
   - Troubleshooting section
   - Configuration examples

## Additional Improvements

### Better Connection Handling
- Retry logic: 3 attempts with 1s, 2s backoff
- Timeout cap at 30 seconds (prevents long hangs)
- Connection: close header (prevents keep-alive issues)

### Pre-flight Checks
- Hostname resolution before attempting HTTP
- Clear indication of which step failed
- Suggestions for each type of failure

### User Guidance
- Web UI URL clearly shown
- Step-by-step instructions
- References to full setup guide

## Testing Recommendations

After flashing the ESP32, verify:

1. **Network connectivity:**
   ```bash
   ping esp-ble-bridge.local
   nslookup esp-ble-bridge.local
   ```

2. **Web interface:**
   - Visit `http://esp-ble-bridge.local/`
   - Check logs show BLE scanner active

3. **ESPHome dashboard:**
   - Device shows as "Online"
   - No errors in logs

4. **BLE scanning:**
   - Logs should show: `[D][ble_scan:XXX]: Device: XX:XX:XX:XX:XX:XX`
   - With lights in pairing mode, should see manufacturer ID `0xfff0`

## Next Steps

1. **Flash the ESP32** using one of the methods above
2. **Verify it's online** and responding
3. **Factory reset a light** to put it in pairing mode
4. **Try pairing** through the Web UI
5. **Check logs** for successful discovery

If you still encounter issues after flashing:
- Check ESP32 logs in ESPHome dashboard
- Verify WiFi credentials in `/config/secrets.yaml`
- Ensure lights are within BLE range (< 10 meters)
- Try with a single light first

## References

- [ESP32 Setup Guide](ESP32_SETUP_GUIDE.md) - Full setup documentation
- [Pairing Guide](PAIRING_GUIDE.md) - Pairing process details
- [Protocol Documentation](BRMESH_PROTOCOL_COMPLETE.md) - Technical reference
