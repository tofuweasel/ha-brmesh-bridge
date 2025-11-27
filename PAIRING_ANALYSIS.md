# BRMesh Pairing Protocol Analysis

## Key Findings from BLE Capture (Nov 27, 2025)

### Advertisement Data Structure

#### Normal Mode (Paired Device)
- **Manufacturer ID:** `0xfff0` (bytes: `[0xf0, 0xff]`)
- **Data Length:** 24 bytes (48 hex characters)
- **Example:** `6db64368931ddd1e07e6b0aa9e64815bd30f66f7cb6b3b5d`
- **Pattern:** Appears to contain device state, mesh routing info

#### Pairing Mode (Factory Reset)
- **Manufacturer ID:** `0xfff0` (same as normal)
- **Data Length:** 16 bytes (32 hex characters) ⭐ **KEY IDENTIFIER**
- **Example Patterns:**
  - `4e5f6b1c348e89b5a88ba1a85e367bc4`
  - `4e5c6b1d348e89b5a88ba1a85e367bc4`
  - `6e517446443d3332340a393930323336`

**Pairing Mode Detection Rule:**
```python
if manufacturer_id == 0xfff0 and len(manufacturer_data) == 16:
    # Device is in pairing mode!
```

### Pairing Protocol Discovery

**NO GATT WRITES DETECTED** ⚠️

This is the critical finding. Analysis of 49,826 BLE packets showed:
- ❌ No ATT Write Request (0x52) packets
- ❌ No ATT Write Command (0x12) packets  
- ❌ No direct BLE connection to unpaired device

**Conclusion:** Pairing happens **over the mesh network**, not via direct BLE connection!

### Pairing Workflow

```
┌─────────────────┐
│  Factory Reset  │
│    (5 blinks)   │
└────────┬────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Advertisement Changes          │
│  48 bytes → 16 bytes            │
│  (Frame 35800 in capture)       │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  App Detects Pairing Mode       │
│  (16-byte manufacturer data)    │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Pairing Command Sent           │
│  Via Mesh Network               │
│  (Through already-paired light) │
└────────┬────────────────────────┘
         │
         ▼
┌─────────────────────────────────┐
│  Device Joins Mesh              │
│  Auto-assigned device ID        │
│  Switches to 24-byte mode       │
└─────────────────────────────────┘
```

### Implementation Requirements

To implement pairing in ESP32 bridge:

1. **Detection Phase**
   - Scan for BRMesh devices (`0xfff0`)
   - Filter for 16-byte manufacturer data = pairing mode
   - Display in UI as "unpaired devices"

2. **Pairing Phase** (NOT YET IMPLEMENTED)
   - ESP32 must already be part of mesh
   - Send pairing command through mesh protocol
   - Command format: TBD (needs reverse engineering)
   - Includes: device ID assignment, mesh key provisioning

3. **Verification Phase**
   - Device advertisement changes to 24-byte mode
   - Device responds to mesh commands
   - Added to network topology

### Current Status (v0.30.20)

✅ **Implemented:**
- Pairing mode detection (16-byte vs 24-byte)
- UI with device cards and Ignore/Pair buttons
- Auto-pair checkbox (experimental)
- Real-time SSE progress during scanning

❌ **Not Yet Implemented:**
- Mesh pairing protocol (ESP32 not in mesh yet)
- Device ID assignment logic
- Mesh key provisioning commands
- Pairing response validation

### Advertisement Pattern Details

**16 Unique Pairing Mode Patterns Observed:**
- First byte: `0x4e` or `0x6e` (command type?)
- Second byte: Rolling counter/nonce (`0x5a`, `0x5c`, `0x5d`, `0x5f`, etc.)
- Remaining bytes: Fixed per session (encryption/session ID?)

Example progression:
```
Frame 35800: 4e5f6b1c348e89b5a88ba1a85e367bc4  (byte[1]=0x5f)
Frame 35801: 4e5f6b1c348e89b5a88ba1a85e367bc4  (byte[1]=0x5f) 
Frame 35802: 4e5f6b1c348e89b5a88ba1a85e367bc4  (byte[1]=0x5f)
...
Frame 35819: 4e5c6b1d348e89b5a88ba1a85e367bc4  (byte[1]=0x5c)
```

### Tools Used

- **Wireshark 4.6.1** - BLE packet analysis
- **tshark** - Command-line packet filtering
- **adb bugreport** - Android BLE HCI log extraction
- **Python scripts** - Pattern analysis

### Next Steps

1. Analyze existing BRMesh mesh protocol captures
2. Identify pairing command packet structure
3. Implement mesh protocol in ESPHome firmware
4. Test pairing through ESP32 bridge
5. Validate with real hardware

### References

- Capture file: `fresh_pairing_capture.log` (8.4 MB, 49,826 packets)
- Analysis script: `analyze_pairing_ads.py`
- Device: BRMesh LED light (factory reset test)
- App: BRMesh v2.0.5 (Android)
