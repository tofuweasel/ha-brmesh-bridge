# BRMesh Light Pairing Guide

## Understanding Mesh Keys

The **mesh key** is an 8-character hex string (like `30323336`) that all lights and controllers in your mesh network must share. It's generated when you first install the BRMesh app and is shared with lights during pairing.

### Generating a New Mesh Key

If you want to start fresh with a new mesh network:

```python
# Generate a random 8-character hex mesh key
import secrets
mesh_key = ''.join(f'{secrets.randbelow(256):02x}' for _ in range(4))
print(f"New mesh key: {mesh_key}")
```

Or use this one-liner in Python:
```bash
python3 -c "import secrets; print(''.join(f'{secrets.randbelow(256):02x}' for _ in range(4)))"
```

**Example output:** `a7f3c2b9`

### Option 1: Re-Pair Lights with BRMesh App (Recommended)

This is the easiest method to get lights onto your Home Assistant mesh:

1. **Factory reset one light**
   - Power cycle it 5 times (on for 2 seconds, off for 2 seconds)
   - OR hold the physical button during power-on (if available)
   - Light should blink rapidly indicating pairing mode

2. **Uninstall and reinstall the BRMesh app**
   - This generates a fresh mesh key
   - Or clear the app's data in Android settings

3. **Pair the light in the BRMesh app**
   - Open the app, tap "Add Device"
   - Light should connect and get assigned a light ID

4. **Extract the new mesh key**
   ```bash
   adb logcat -c
   # Control the light in the app
   adb logcat -d | grep "mesh_key\|jyq_helper"
   ```
   
   Look for: `mesh_key: a7f3c2b9` (your key will differ)

5. **Update your Home Assistant configuration**
   - Add-on Settings → Change mesh_key to your new key
   - ESPHome YAML → Update `mesh_key: "a7f3c2b9"`
   - Reflash your ESP32

6. **Pair more lights**
   - Factory reset them
   - Pair in BRMesh app
   - They'll automatically join your mesh
   - Extract light IDs from logcat: `payload: 220a00...` (0x0a = light ID 10)

### Option 2: Use Existing BRMesh App Mesh

If you already have lights paired in the BRMesh app:

1. **Extract current mesh key**
   ```bash
   adb logcat -c
   # Control any light in the BRMesh app
   adb logcat -d | grep "mesh_key"
   ```

2. **Update Home Assistant config**
   - Use the extracted mesh key in your add-on settings
   - Update ESPHome YAML with the same key

3. **Extract light IDs**
   ```bash
   adb logcat -c
   # Control each light one at a time in the app
   adb logcat -d | grep "payload:"
   ```
   
   Example output: `payload: 220aff00ff0064010000000000`
   - Byte 1: `22` = command
   - **Byte 2: `0a` = light ID 10** ← This is what you need!
   - Remaining bytes: color/brightness data

4. **Add lights to Home Assistant**
   - Add-on Web UI → manually add each light with its ID
   - OR let the add-on scan and discover them

### Option 3: Fresh Start (All Devices)

If you want complete control and a fresh mesh:

1. **Generate new mesh key** (see above)

2. **Factory reset ALL your lights**
   - Power cycle each 5 times
   - Ensure they enter pairing mode (rapid blinking)

3. **Update ESP32 with new mesh key**
   ```yaml
   fastcon:
     mesh_key: "YOUR_NEW_KEY_HERE"
   ```
   - Reflash ESP32

4. **Manually pair lights using ESP32**
   - Power on one light in pairing mode
   - ESP32 will detect it via BLE
   - Assign it a light ID (1-255)
   - Repeat for each light

   **Note:** Manual ESP32 pairing is complex. Using the BRMesh app is recommended.

## Troubleshooting

### Light won't enter pairing mode
- Try 10 power cycles instead of 5
- Hold physical button during power-on (if available)
- Check if light is already paired (solid color = paired)

### ESP32 not controlling lights
- ✅ Verify mesh keys match exactly (case-sensitive hex)
- ✅ Check ESP32 logs for BLE errors
- ✅ Ensure lights are within BLE range (~30 feet)
- ✅ Verify light IDs are correct (use logcat)

### Command queue full errors
- ✅ Add `throttle: 300ms` to each light in YAML (already done in v0.20.0+)
- ✅ Remove unused light definitions (only define lights you have)
- ✅ Check for HA automations rapidly toggling lights

### Add-on not showing lights
- The add-on needs lights to be **manually added** or **scanned**
- Go to Settings → Configure lights in the web UI
- OR import from BRMesh app via ADB
- The add-on doesn't auto-discover without explicit configuration

## Current Setup Process (Recommended)

1. **Keep your existing BRMesh app setup** (don't uninstall)
2. **Extract mesh key and light IDs** via ADB logcat
3. **Configure Home Assistant**:
   - Set mesh_key in add-on settings
   - Add lights manually in web UI with correct IDs
4. **Flash ESP32** with matching mesh_key
5. **Control via Home Assistant** while keeping BRMesh app as backup

This way you have both systems working simultaneously!

## Mesh Key Format

Valid mesh key examples:
- `30323336` ✅
- `a7f3c2b9` ✅
- `00112233` ✅

Invalid:
- `3032` ❌ (too short, must be 8 chars)
- `GGHHIIJJ` ❌ (must be hex: 0-9, a-f only)
- `3032 3336` ❌ (no spaces allowed)

---

**Need help?** Check the add-on logs and ESP32 logs for detailed error messages.
