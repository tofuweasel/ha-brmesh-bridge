# BRMesh Multi-Bridge Deployment Guide

## Overview

You have two options for adding additional ESP32s to extend your BRMesh network range:

1. **Bluetooth Proxy** (Simpler) - Just extends BLE range
2. **Full Bridge** (Advanced) - Independent controller with full protocol support

---

## Option 1: Bluetooth Proxy (Recommended for Most Users)

### What it does:
- Extends BLE range for your main BRMesh Bridge
- Purely passive relay - no protocol handling
- Multiple proxies can coexist without conflicts
- Automatically discovered by Home Assistant

### When to use:
- ✅ You need to reach distant lights
- ✅ You want simple setup
- ✅ Your main bridge handles all logic
- ✅ You just need range extension

### Setup:

1. **Flash new ESP32 with proxy firmware:**
   ```yaml
   # Use: esphome/brmesh-proxy-only.yaml
   ```

2. **Configure ESPHome:**
   - Update `secrets.yaml` with WiFi credentials
   - Generate new API encryption key
   - Flash to ESP32

3. **That's it!**
   - Home Assistant will auto-discover it
   - It will appear as a Bluetooth proxy device
   - Your main BRMesh Bridge addon will use it automatically

### Architecture:
```
[Phone/HA]
     ↓
[BRMesh Bridge Addon (Python)]
     ↓
     ├── [Main ESP32 Bridge] ----BLE----> [Lights in range]
     │
     └── [ESP32 Proxy #1] -------BLE----> [Distant lights]
         [ESP32 Proxy #2] -------BLE----> [More distant lights]
```

**Key Points:**
- Only ONE device runs the Python addon
- Multiple ESP32s act as "BLE antennas"
- All protocol logic stays in one place
- Simple to manage and debug

---

## Option 2: Full Bridge (Advanced)

### What it does:
- Complete independent BRMesh controller
- Handles full protocol encryption/decryption
- Can work standalone without main addon
- More redundancy and reliability

### When to use:
- ✅ Large property with multiple zones
- ✅ You want independent control
- ✅ You need high availability
- ✅ Main addon goes down, lights still work

### Setup:

1. **Flash new ESP32 with full bridge firmware:**
   ```yaml
   # Use: esphome/brmesh-bridge-optimized.yaml
   ```

2. **Configure second addon instance:**
   - Install ESP BLE Bridge addon again (different name)
   - Configure with SAME mesh key
   - Add DIFFERENT ESP32 controller
   - Configure separate lights OR share light list

3. **Light assignment options:**
   
   **Option A: Zone-based (Recommended)**
   - Bridge #1: Front yard lights (IDs 1-10)
   - Bridge #2: Back yard lights (IDs 11-20)
   - Each bridge controls its zone
   - Cleaner organization

   **Option B: Shared control**
   - Both bridges control ALL lights
   - Better redundancy
   - More complex coordination

### Architecture:
```
[Phone/HA]
     ↓
     ├── [BRMesh Bridge Addon #1 (Python)]
     │        ↓
     │   [ESP32 Bridge #1] --BLE--> [Front yard lights]
     │
     └── [BRMesh Bridge Addon #2 (Python)]
              ↓
         [ESP32 Bridge #2] --BLE--> [Back yard lights]
```

**Key Points:**
- TWO separate addon instances
- TWO separate Python processes
- Each has own web UI
- Must share same mesh key
- More complex but more capable

---

## Mesh Forwarding Feature

### What is it?

The `forward` flag in BRMesh protocol controls whether lights relay commands to other lights.

- **forward=1** (Default): Commands hop through the mesh
- **forward=0**: Direct BLE range only

### Where to configure:

1. **ESPHome firmware switch:**
   ```yaml
   switch:
     - platform: template
       name: "Mesh Forwarding"
       id: mesh_forward
       restore_mode: RESTORE_DEFAULT_ON  # On by default
   ```

2. **Home Assistant entity:**
   - Each ESP32 Bridge has a "Mesh Forwarding" switch
   - Toggle in HA UI
   - Affects ALL commands from that bridge

3. **Per-light setting (Future):**
   - Not yet implemented
   - Would allow per-light mesh forward control
   - Useful for testing range issues

### How it works:

**With forwarding ON (forward=1):**
```
[Bridge] --BLE--> [Light A] --relay--> [Light B] --relay--> [Light C]
```
✅ Can control distant lights  
✅ More reliable in large spaces  
⚠️ Slight delay as commands hop (~50-100ms per hop)  
⚠️ Each relay = one additional BLE broadcast (minimal traffic)  

**With forwarding OFF (forward=0):**
```
[Bridge] --BLE--> [Light A]  (Light B & C not reached)
```
✅ Faster response (instant)  
✅ Less mesh traffic (no relays)  
❌ Only direct BLE range works (~10-30m)  

### Traffic Impact:

**forward=1 overhead:**
- Each light in range rebroadcasts the command once
- 24-byte command × number of mesh hops
- Example: 5 lights in range = 5 × 24 bytes = 120 bytes total
- **This is negligible** - BLE can handle thousands of packets/second
- Commands are sent ~3-5 times/second max (when actively controlling)

**Recommendation:** Leave forward=1 enabled unless:
- You're debugging direct range issues
- You have 50+ densely packed lights causing rare packet collisions
- You need absolute minimum latency (< 100ms difference)  

### When to disable forwarding:

- Testing BLE range issues
- Debugging which lights are in direct range
- Reducing mesh chatter in dense networks
- Troubleshooting command conflicts

---

## Recommendations

### For most homes (< 20 lights):
- 1x Full Bridge (main controller)
- 1-2x Bluetooth Proxies (range extension)

### For large properties (20+ lights):
- 2-3x Full Bridges (zone-based)
- 2-4x Bluetooth Proxies (fill dead zones)

### For apartments/small spaces:
- 1x Full Bridge (no proxies needed)

---

## Troubleshooting

### Proxies not discovered:
1. Check Home Assistant → Integrations → ESPHome
2. Verify WiFi connection (check ESP logs)
3. Ensure `bluetooth_proxy: active: true` in YAML

### Multiple bridges conflicting:
1. Verify SAME mesh key on all bridges
2. Use different ESP32 names
3. Check addon logs for command duplicates
4. Consider zone-based light assignment

### Lights not responding with forwarding OFF:
1. Check RSSI values (should be > -70 dBm)
2. Move bridge closer OR enable forwarding
3. Add Bluetooth proxy between bridge and light

### Commands delayed:
1. This is normal with multi-hop mesh
2. Disable forwarding if you need instant response
3. Add more bridges to reduce hop count

---

## Advanced: Mesh Network Design

### Good mesh topology:
```
        [Bridge]
       /    |    \
    [L1]  [L2]  [L3]
           |       |
         [L4]    [L5]
```
- 2-3 hops maximum
- Multiple paths to distant lights
- Bridge centrally located

### Bad mesh topology:
```
[Bridge] -> [L1] -> [L2] -> [L3] -> [L4] -> [L5]
```
- Long chain = delays
- Single point of failure
- Consider adding bridge or proxy mid-chain

---

## Version History

- **v0.30.7**: Added mesh forwarding toggle
- **v0.30.6**: Real BLE discovery
- **v1.0.0**: Initial firmware release
