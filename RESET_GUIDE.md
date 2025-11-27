# BRMesh Bridge - Reset & Recovery Guide

Complete guide for resetting lights, controllers, and the entire system.

---

## Table of Contents

1. [Factory Reset Light](#factory-reset-light)
2. [Remove Light (Unpair)](#remove-light-unpair)
3. [Reset Controller](#reset-controller)
4. [Full System Reset](#full-system-reset)
5. [Recovery Procedures](#recovery-procedures)
6. [Troubleshooting](#troubleshooting)

---

## Factory Reset Light

**Purpose:** Clear the light's pairing data and return it to pairing mode.

### When to Use

- Light is unresponsive or behaving erratically
- Want to re-pair light with a different mesh
- Selling/giving away the light
- Light stopped responding to commands

### How It Works

The factory reset command sends a BLE broadcast to the light:
```
Command: 0xF0 0xFF <light_id> 0x00 0x00 0x00 0x00 0x00
```

This tells the light to:
1. Erase its mesh configuration
2. Clear pairing data
3. Prepare to enter pairing mode

### Steps

**Via Web UI:**

1. Open Web UI → **Lights** tab
2. Find the light you want to reset
3. Click **🔄 Reset** button
4. Confirm the action
5. **Power cycle the light** (turn off and on)
6. Light will enter pairing mode (usually blinks rapidly)
7. Re-pair using the BRMesh app or discovery scan

**Via API:**

```bash
curl -X POST http://homeassistant.local:8099/api/lights/10/reset
```

Replace `10` with your light ID.

**Response:**
```json
{
  "success": true,
  "message": "Light 10 has been factory reset. Power cycle the light to enter pairing mode."
}
```

### Important Notes

⚠️ **The light will NOT automatically enter pairing mode**. You must power cycle it (turn off and back on).

✅ **The light remains in your configuration** until you remove it separately.

🔄 **After reset**, re-pair the light:
- Option 1: Use BRMesh app to pair
- Option 2: Use Web UI **🔍 Scan for Lights** to auto-discover

---

## Remove Light (Unpair)

**Purpose:** Remove a light from the system without factory resetting it.

### When to Use

- Light is no longer in use
- Light was physically removed/replaced
- Cleaning up unused devices
- Light was added by mistake

### What It Does

1. Removes light from Home Assistant (unpublishes MQTT discovery)
2. Deletes light from configuration file
3. Removes light from all ESPHome configs
4. Light remains paired with mesh (can still be controlled by BRMesh app)

### Steps

**Via Web UI:**

1. Open Web UI → **Lights** tab
2. Find the light you want to remove
3. Click **🗑️ Remove** button
4. Confirm the action
5. Light disappears from all interfaces

**Via API:**

```bash
curl -X POST http://homeassistant.local:8099/api/lights/10/unpair
```

**Response:**
```json
{
  "success": true,
  "message": "Light 10 (Living Room) has been removed from configuration"
}
```

### Important Notes

⚠️ **This does NOT factory reset the light**. It only removes it from your Home Assistant.

✅ **The light still works** with the BRMesh app and other controllers on the same mesh.

🔄 **To completely remove** the light from the mesh, use Factory Reset instead.

---

## Reset Controller

**Purpose:** Remove an ESP32 controller from the system.

### When to Use

- Controller is no longer in use
- Want to reconfigure controller from scratch
- Controller was replaced
- Troubleshooting controller issues

### What It Does

1. Removes controller from configuration
2. Deletes ESPHome YAML file (`/config/esphome/{name}.yaml`)
3. Lights remain configured and work with other controllers
4. Controller can be re-added as new

### Steps

**Via Web UI:**

1. Open Web UI → **Controllers** tab
2. Find the controller you want to reset
3. Click **🔄 Reset** button
4. Confirm the action
5. Controller is removed

**Via API:**

```bash
curl -X POST http://homeassistant.local:8099/api/controllers/brmesh-bridge/reset
```

Replace `brmesh-bridge` with your controller name.

**Response:**
```json
{
  "success": true,
  "message": "Controller brmesh-bridge has been reset. You can add it again as a new controller."
}
```

### Important Notes

⚠️ **This does NOT erase the ESP32's firmware**. The ESP32 keeps running with old config.

✅ **Lights are NOT affected**. They continue working with other controllers.

🔄 **To completely wipe the ESP32**, flash new firmware or use ESPHome's "Clean Build Files" option.

---

## Full System Reset

**Purpose:** Remove ALL lights, controllers, scenes, and effects from the system.

### 🚨 DANGER - USE WITH EXTREME CAUTION 🚨

This is a **destructive operation** that cannot be undone!

### What It Does

1. Removes **ALL lights** from Home Assistant
2. Removes **ALL controllers** from configuration
3. Deletes **ALL scenes**
4. Deletes **ALL effects**
5. Removes **ALL ESPHome YAML files** (except secrets.yaml)
6. **Preserves:** Mesh key, MQTT settings, WiFi networks

### When to Use

- Starting completely fresh
- Migrating to new hardware
- Troubleshooting major configuration issues
- Preparing system for sale/transfer

### Steps

**Via Web UI:**

1. Open Web UI → **Settings** tab
2. Scroll to **🚨 Danger Zone**
3. Click **🔥 Full System Reset**
4. Confirm the first warning
5. Type `RESET` (in capital letters) to confirm
6. System resets and page reloads

**Via API:**

```bash
curl -X POST http://homeassistant.local:8099/api/system/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

**Response:**
```json
{
  "success": true,
  "message": "System has been fully reset. All lights, controllers, scenes, and effects have been removed."
}
```

### Important Notes

⚠️ **THIS CANNOT BE UNDONE!** All your configuration will be permanently deleted.

✅ **Preserved data:**
- Mesh key (you can still control lights with BRMesh app)
- MQTT broker settings
- WiFi networks saved in secrets.yaml
- Map coordinates

❌ **Lost data:**
- All light configurations and names
- All controller configurations
- All scenes
- All effects
- All ESPHome YAML files

### Recovery After System Reset

1. **Lights still work** with BRMesh app (mesh key preserved)
2. **Re-discover lights:**
   - Click **🔍 Scan for Lights**
   - Wait 30 seconds
   - Rename lights as needed
3. **Re-create controllers:**
   - Click **Create Controller**
   - Enter WiFi credentials
   - Generate ESPHome config
   - Flash ESP32
4. **Rebuild automations** in Home Assistant

---

## Recovery Procedures

### Recover from Accidental Light Removal

If you removed a light by mistake:

1. **Check if light is still paired:**
   - Try controlling from BRMesh app
   - If works → Light is still on mesh

2. **Re-add to Home Assistant:**
   - Web UI → **🔍 Scan for Lights**
   - Light should be auto-discovered
   - If not found → Factory reset and re-pair

### Recover from Accidental Controller Reset

If you reset a controller by mistake:

1. **Controller still runs** with old config
2. **Re-add controller:**
   - Web UI → **Create Controller** or **Add Existing Controller**
   - Use same name as before
   - Generate and flash new config
3. **All lights still work** with remaining controllers

### Recover from Full System Reset

If you performed a system reset by mistake:

1. **Mesh key is preserved** → Lights still on mesh
2. **MQTT settings preserved** → Broker connection works
3. **Re-scan for devices:**
   ```bash
   # Click Scan for Lights in Web UI
   # Or via API:
   curl -X POST http://homeassistant.local:8099/api/scan
   ```
4. **Regenerate ESPHome configs** for controllers
5. **Rebuild scenes and automations** manually

### Backup Before Reset

**Always backup before major operations:**

```bash
# Export current configuration
curl http://homeassistant.local:8099/api/config > brmesh_backup_$(date +%Y%m%d).json

# Backup ESPHome files
cp -r /config/esphome /backup/esphome_$(date +%Y%m%d)

# Backup secrets
cp /config/secrets.yaml /backup/secrets_$(date +%Y%m%d).yaml
```

---

## Troubleshooting

### Factory Reset Not Working

**Symptom:** Light doesn't enter pairing mode after reset

**Solutions:**
1. **Power cycle multiple times:**
   - Turn off for 10 seconds
   - Turn on and wait 5 seconds
   - Repeat 3-5 times
2. **Check BLE range:**
   - Move ESP32 closer to light
   - Maximum range: ~50 feet
3. **Verify mesh key:**
   - Wrong key = commands ignored
   - Check Settings → Mesh Key
4. **Try physical reset:**
   - Some lights have a physical reset button
   - Press/hold during power-on (check manual)

### Remove Light Failed

**Symptom:** Error when trying to remove light

**Solutions:**
1. **Check light ID:**
   - Verify correct ID in URL/command
2. **MQTT disconnected:**
   - Settings → Check MQTT connection
   - Restart add-on if needed
3. **Manual cleanup:**
   ```bash
   # Remove from Home Assistant manually
   mosquitto_pub -h core-mosquitto -t "homeassistant/light/brmesh_10/config" -m "" -r
   ```

### Controller Reset Failed

**Symptom:** Controller not removed from list

**Solutions:**
1. **File permissions:**
   ```bash
   # Check ESPHome folder permissions
   ls -la /config/esphome/
   # Should be writable by add-on
   ```
2. **Manual removal:**
   ```bash
   rm /config/esphome/brmesh-bridge.yaml
   ```
3. **Edit config directly:**
   - Home Assistant → File Editor
   - `/data/options.json`
   - Remove controller from `controllers` array

### System Reset Stuck

**Symptom:** System reset hangs or fails partway

**Solutions:**
1. **Restart add-on:**
   - Home Assistant → Add-ons → BRMesh Bridge
   - Click **Restart**
2. **Manual reset:**
   ```bash
   # Connect to add-on terminal
   # Remove all configs
   rm /config/esphome/*.yaml
   # Keep secrets.yaml
   cp /backup/secrets.yaml /config/esphome/
   
   # Reset data file
   echo '{"lights":[],"controllers":[],"scenes":[],"effects":[]}' > /data/options.json
   
   # Restart add-on
   ```
3. **Check logs:**
   - Supervisor → BRMesh Bridge → Logs
   - Look for error messages

---

## API Reference

### Reset Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/lights/<id>/reset` | POST | Factory reset a light |
| `/api/lights/<id>/unpair` | POST | Remove light from system |
| `/api/controllers/<name>/reset` | POST | Reset a controller |
| `/api/system/reset` | POST | Full system reset (requires `{"confirm": true}`) |

### Example Usage

**Factory Reset Light 10:**
```bash
curl -X POST http://homeassistant.local:8099/api/lights/10/reset
```

**Remove Light 15:**
```bash
curl -X POST http://homeassistant.local:8099/api/lights/15/unpair
```

**Reset Controller:**
```bash
curl -X POST http://homeassistant.local:8099/api/controllers/brmesh-bridge-1/reset
```

**Full System Reset:**
```bash
curl -X POST http://homeassistant.local:8099/api/system/reset \
  -H "Content-Type: application/json" \
  -d '{"confirm": true}'
```

---

## Best Practices

### Before Resetting

✅ **Backup your configuration**
✅ **Document light IDs and names**
✅ **Take screenshots of scenes**
✅ **Export automations** from Home Assistant
✅ **Test with one light first**

### After Resetting

✅ **Power cycle affected devices**
✅ **Verify MQTT connectivity**
✅ **Regenerate ESPHome configs**
✅ **Test basic operations** before rebuilding complex scenes
✅ **Update documentation** with new IDs/names

### Safety Tips

⚠️ **Don't reset during firmware updates**
⚠️ **Don't reset if MQTT is down** (can cause inconsistent state)
⚠️ **Don't factory reset lights** unless necessary (pairing can be time-consuming)
⚠️ **Always backup before system reset**

---

## Common Scenarios

### Scenario 1: Replace a Broken Light

1. Remove old light: Click **🗑️ Remove**
2. Power on new light
3. Click **🔍 Scan for Lights**
4. Rename to match old light
5. Update scenes/automations if needed

### Scenario 2: Move Light to Another Room

1. Don't reset! Just rename:
   - Edit light name in Web UI
   - Update automations in Home Assistant
2. Update map position if using Map View

### Scenario 3: Troubleshoot Unresponsive Light

1. Try toggling On/Off first
2. Check MQTT connection
3. Verify mesh key is correct
4. If still unresponsive → Factory Reset
5. Power cycle and re-pair

### Scenario 4: Start Fresh After Testing

1. **Full System Reset** in Settings → Danger Zone
2. Re-scan for lights: **🔍 Scan for Lights**
3. Re-create controllers
4. Rebuild scenes as needed

---

## Support

- **Web UI:** http://homeassistant.local:8099
- **Logs:** Supervisor → BRMesh Bridge → Logs
- **Config:** `/config/esphome/*.yaml`
- **Data:** `/data/options.json`

For persistent issues:
1. Check logs for error messages
2. Verify mesh key matches BRMesh app
3. Test with physical BRMesh app first
4. Restart add-on if needed

---

**Last Updated:** v0.19.0 - Reset package implementation

