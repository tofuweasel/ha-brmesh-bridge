# BRMesh Protocol Analysis Summary

## Successfully Decoded from Pairing Capture

### Pairing Protocol
- **Manufacturer Data**: 0xff type, manufacturer 0xf0ff
- **Payload Format**: 12 bytes
  ```
  [DeviceID: 6 bytes][LightID: 2 bytes][MeshKey: 4 bytes]
  ```
- **Example Pairing Messages**:
  - Device 1: `348e89b5a88b 1201 30323336` → "Light a88b"
  - Device 2: `348e89b5e238 1301 30323336` → "Light e238"

### Device Naming
- App uses last 4 hex digits of DeviceID
- Format: "Light XXXX" where XXXX = last 4 hex of device ID

### Light ID Assignment
- 2-byte field in pairing payload
- Pattern observed: 1201, 1301, 1401...
- First byte increments per device (12→13→14)
- Second byte appears to be device type or sequence

### Mesh Configuration
- **Mesh Key**: `30323336` (ASCII "0236")
- **Encryption Key**: `5e367bc4` (derived from mesh key)
- Key derivation likely uses proprietary algorithm

## Unknown - Requires Further Investigation

### Scene Protocol
Without the decrypted app config, we need to capture scene activation:

**Recommended capture process:**
1. Enable ADB logcat filtering for BRMesh
2. Activate a scene in the app
3. Capture the BLE commands sent
4. Analyze payload structure

**Expected scene data structure:**
- Scene ID (unknown size)
- Light states per device:
  - On/Off
  - Brightness (0-100 or 0-255)
  - Color (RGB or HSV)
  - Color temperature (if applicable)

### Group Protocol
Similarly, need to capture group commands:

**Capture process:**
1. Control a group from the app
2. Monitor BLE traffic
3. Identify group addressing mechanism

**Expected group structure:**
- Group ID
- Member light IDs
- Group commands (same as individual light commands?)

### Command Structure Analysis
From existing implementation, commands use:
- Destination address (light ID)
- Opcode (command type)
- Parameters (brightness, color, etc.)
- Need to identify:
  - Scene activation opcode
  - Group addressing format
  - Scene-specific parameters

## Implementation Strategy

### Phase 1: Capture More Protocol Data
1. **Scene Activation Capture**
   ```bash
   adb logcat -c
   adb logcat | grep -E "BRMesh|payload|scene" > scene_capture.txt
   # Activate scenes in app
   ```

2. **Group Control Capture**
   ```bash
   adb logcat -c
   adb logcat | grep -E "BRMesh|payload|group" > group_capture.txt
   # Control groups in app
   ```

3. **Device Metadata Capture**
   ```bash
   adb logcat -c
   adb logcat > full_app_usage.txt
   # Use all app features
   ```

### Phase 2: Protocol Analysis
1. Analyze captured payloads
2. Identify scene/group opcodes
3. Map scene definitions to commands
4. Document group addressing

### Phase 3: Addon Implementation
1. **Scene Support**
   - Add scene entity definitions
   - Implement scene activation commands
   - Store scene configurations
   - Map to HA scene entities

2. **Group Support**
   - Parse group definitions
   - Create HA light group entities
   - Implement group commands
   - Handle group state updates

3. **Native ESP32 Pairing**
   - Add BLE scanner to ESP32
   - Scan for manufacturer data (0xf0ff)
   - Parse 12-byte pairing payload
   - Auto-assign next light ID
   - Update addon config

### Phase 4: Testing
1. Test scene activation
2. Test group control
3. Test native pairing workflow
4. Validate all 15 lights

## Current Status

### ✅ Completed
- Pairing protocol fully decoded
- Device ID format understood
- Mesh key identified
- Light ID pattern documented

### ⏳ In Progress
- Attempting to decrypt app export (unsuccessful - proprietary encryption)

### ⏸️ Pending
- Scene protocol capture and analysis
- Group protocol capture and analysis
- Scene/group implementation in addon
- Native ESP32 pairing implementation

## Alternative Approaches

### 1. Reverse Engineer App APK
- Decompile BRMesh APK
- Analyze encryption/protocol code
- Extract scene/group data structures
- **Difficulty**: High (obfuscation likely)

### 2. Network Traffic Analysis
- Use Wireshark/tcpdump on Android
- Capture BLE HCI logs
- Analyze at packet level
- **Difficulty**: Medium (requires rooted device)

### 3. Progressive Feature Capture
- Capture each feature individually via logcat
- Build protocol documentation incrementally
- **Difficulty**: Low (current approach)
- **Recommended**: ✓ This is the best approach

## Next Steps

1. **User Action Required**: Capture scene/group usage via ADB logcat
2. **Agent**: Analyze captures to decode protocols
3. **Implementation**: Add scene and group support to addon
4. **Testing**: Validate with full 15-light setup

## Notes

- The QR codes shown are for phone-to-phone mesh sharing
- They likely contain encrypted mesh configuration
- Decryption requires device-specific or mesh-specific keys
- The proprietary encryption is not essential for our needs
- We can reverse-engineer the protocol through observation
