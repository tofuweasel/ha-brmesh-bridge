# BRMesh BLE Pairing Protocol Analysis

## Capture Plan

### Step 1: Capture Pairing Process

```bash
# Clear logcat buffer
adb logcat -c

# Start capturing with BLE filters
adb logcat | grep -E "mesh|ble|pair|fastcon|jyq|payload" > pairing_capture.txt

# Now in BRMesh app:
# 1. Factory reset a light (5 power cycles)
# 2. Tap "Add Device"
# 3. Wait for pairing to complete
# 4. Control the light once (toggle on/off)
# 5. Stop capture (Ctrl+C)
```

### Step 2: What We're Looking For

**Key Information to Extract:**

1. **Pairing BLE Advertisement**
   - Service UUIDs during pairing mode
   - Manufacturer data format
   - Device name pattern
   - RSSI/signal strength

2. **Pairing Commands Sent**
   - Initial handshake packets
   - Mesh key exchange format
   - Light ID assignment command
   - Confirmation/acknowledgment

3. **Post-Pairing Behavior**
   - How light acknowledges pairing
   - First control command format
   - Light state synchronization

### Step 3: Analyze Captured Data

Look for these patterns:

```
# Pairing mode advertisement
[SERVICE_UUID] 0000fff0-... (likely service UUID)
[MANUFACTURER_DATA] <hex bytes>

# Pairing command sequence
payload: <HEX>  # Command to assign mesh key + light ID
payload: <HEX>  # Confirmation
payload: <HEX>  # First control command
```

## Expected Pairing Protocol

Based on BRMesh/Fastcon protocol knowledge:

### Pairing Mode Detection
- Light in pairing mode broadcasts special BLE advertisement
- Service UUID: `0000fff0-0000-1000-8000-00805f9b34fb` (likely)
- Characteristic: `0000fff3-...` (write) and `0000fff4-...` (notify)

### Pairing Command Format (Hypothesis)

```
Byte 0: Command (0xF0 = pairing?)
Byte 1: Sub-command
Bytes 2-5: Mesh key (4 bytes)
Byte 6: Assigned light ID
Bytes 7+: Checksum/padding
```

### ESP32 Implementation Plan

Once we capture the real pairing sequence:

1. **Add pairing mode detection**
   ```yaml
   # In ESPHome YAML
   binary_sensor:
     - platform: gpio
       id: pairing_button
       pin:
         number: GPIO0
         inverted: true
       on_press:
         then:
           - lambda: |-
               // Trigger pairing scan
               ESP_LOGI("pairing", "Scanning for lights in pairing mode...");
   ```

2. **BLE Scanner for Pairing Mode Lights**
   ```cpp
   // Scan for devices advertising pairing mode
   // Filter by service UUID or manufacturer data
   // Display available lights to pair
   ```

3. **Send Pairing Commands**
   ```cpp
   // Build pairing packet with mesh_key and next_available_light_id
   // Send to discovered device
   // Wait for confirmation
   // Add to configured lights
   ```

4. **Web UI Integration**
   - Add "Pair New Light" button
   - Calls ESP32 pairing function via service
   - Shows discovered lights
   - Assigns next available ID automatically

## Capture Commands Reference

### Start Comprehensive Capture
```bash
# Capture everything BLE-related
adb logcat -b all | tee full_pairing_capture.txt

# Or filtered for BRMesh specifically
adb logcat | grep -iE "mesh|fastcon|fff[0-4]|jyq|0x22|0xf0" | tee pairing_filtered.txt
```

### Capture HCI (Bluetooth Low-Level)
```bash
# Enable HCI snoop logging on Android
adb shell settings put secure bluetooth_hci_log 1

# Restart Bluetooth
adb shell svc bluetooth disable
adb shell svc bluetooth enable

# Perform pairing in app

# Pull HCI snoop log
adb pull /sdcard/btsnoop_hci.log

# Disable HCI logging when done
adb shell settings put secure bluetooth_hci_log 0
```

Then analyze `btsnoop_hci.log` in Wireshark:
- File → Open → btsnoop_hci.log
- Filter: `bluetooth.uuid == 0xfff0` or similar
- Look for GATT Write operations during pairing

## Next Steps After Capture

1. **Paste captured output** here for analysis
2. **Identify pairing command** hex pattern
3. **Implement in ESPHome** custom component
4. **Add to BRMesh Bridge addon** as pairing API
5. **Test with factory reset light**

## Example Pairing Sequence (To Be Confirmed)

```
# Hypothetical - will confirm with real capture:

[SCAN] Device found: "MESH_UNPAIRED_XXXX"
[CONNECT] Connecting to device...
[DISCOVER] Services: fff0, fff3, fff4
[WRITE] fff3 <- F0 01 30 32 33 36 0A 00 00 00 00 00  # Pair with key 30323336, assign ID 10
[NOTIFY] fff4 -> F0 81 0A  # Acknowledgment: Light ID 10 paired
[WRITE] fff3 <- 22 0A FF 00 00 64 01 00 00 00 00 00  # First control: Turn on white at full brightness
[NOTIFY] fff4 -> 22 81 0A  # Ack: Command received
```

---

**Ready to capture?** Run the commands above and paste the output for analysis!
