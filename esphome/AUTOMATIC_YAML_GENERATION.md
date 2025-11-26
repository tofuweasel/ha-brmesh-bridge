# Automatic Optimized YAML Generation

## Overview

The BRMesh Bridge addon now automatically generates optimized ESPHome configurations that use the `tofuweasel/esphome-fastcon@optimized` fork instead of the standard `scross01/esphome-fastcon@dev`.

## What's Different?

### Optimized Mode (Default)
- **Command Optimization**: Uses the optimized fork with built-in debouncing (100ms), deduplication, and minimum interval (300ms)
- **66% Fewer Commands**: Reduces command spam from 9 commands → 3 commands when turning off 3 lights
- **BLE Scanner**: Includes `esp32_ble_tracker` to detect unpaired BRMesh lights (manufacturer_id: 0xf0ff)
- **Pairing Mode**: Template switch to enable/disable pairing mode (logging only, custom component planned)
- **Start with 0 Lights**: When no lights are configured, generates empty light section with helpful comments
- **No Throttle Parameter**: Optimization is built into the component, no need for external throttling

### Standard Mode
- **Original Fork**: Uses `scross01/esphome-fastcon@dev`
- **Manual Throttling**: Includes `throttle: 300ms` parameter on each light
- **Pre-populated Lights**: Generates 15 lights by default if none configured
- **BLE Server**: Uses `esp32_ble_server` component

## Configuration

The addon uses optimized mode by default. To switch to standard mode:

```python
# In brmesh_bridge.py config:
'use_optimized_fork': False  # Default: True
```

Or programmatically:
```python
bridge.config['use_optimized_fork'] = False
```

## Generated YAML Examples

### Optimized Mode with 0 Lights

```yaml
external_components:
  - source: github://tofuweasel/esphome-fastcon@optimized
    components: [fastcon]

esp32_ble_tracker:
  on_ble_advertise:
    - then:
        - lambda: |-
            // Detects unpaired BRMesh lights (0xf0ff)

switch:
  - platform: template
    name: "Pairing Mode"
    id: pairing_mode

light: []
# To add lights after pairing, uncomment and modify:
# - platform: fastcon
#   id: brmesh_light_01
#   name: "Living Room Light"
#   light_id: 1
```

### Optimized Mode with Configured Lights

```yaml
external_components:
  - source: github://tofuweasel/esphome-fastcon@optimized
    components: [fastcon]

light:
  - platform: fastcon
    id: brmesh_light_01
    name: "Living Room"
    light_id: 1
    color_interlock: true
    # No throttle parameter - built into component!
```

### Standard Mode

```yaml
external_components:
  - source: github://scross01/esphome-fastcon@dev
    components: [fastcon]

esp32_ble_server: {}  # Not esp32_ble_tracker

light:
  - platform: fastcon
    id: brmesh_light_01
    name: "Living Room"
    light_id: 1
    color_interlock: true
    throttle: 300ms  # External throttling required
```

## Performance Improvements

### Command Reduction
- **Turning off 3 lights sequentially**:
  - Standard mode: 9 commands (3 per light × 3 lights)
  - Optimized mode: 3 commands (1 per light)
  - **Improvement**: 66% fewer commands

- **Changing brightness slider**:
  - Standard mode: 10-15 commands (continuous updates)
  - Optimized mode: 1-2 commands (debounced)
  - **Improvement**: 80-90% fewer commands

### Response Time
- **Standard mode**: 540ms for 3 lights (9 commands × 60ms each)
- **Optimized mode**: 180ms for 3 lights (3 commands × 60ms each)
- **Improvement**: 66% faster

## Usage

1. **Fresh Pairing** (Recommended):
   - Delete all lights from addon config
   - Regenerate YAML (will create optimized config with 0 lights)
   - Flash ESP32
   - Enable "Pairing Mode" switch
   - Reset lights (hold button 5s until triple flash)
   - Wait for BLE scanner to detect lights
   - Manually add light entries to YAML (see template comments)
   - Reflash ESP32

2. **Existing Lights**:
   - Keep your current light configuration
   - Regenerate YAML (will create optimized config with your lights)
   - Flash ESP32
   - Lights will work immediately with reduced command spam

## Testing

Run the test script to verify YAML generation:

```bash
cd /path/to/addon/esphome
python test_yaml_generation.py
```

This will show:
- Optimized mode with 0 lights
- Standard mode with 3 lights
- Optimized mode with 3 lights

## Troubleshooting

### ESPHome Compilation Fails
- Check that you're using ESPHome 2023.12.0 or later
- Verify ESP32 is selected (not ESP8266)
- Check logs for specific error messages

### Lights Not Pairing
- Ensure "Pairing Mode" switch is turned on
- Verify lights are reset (hold button 5s, triple flash)
- Check ESP32 logs for "Found unpaired BRMesh light" messages
- Ensure BLE scanner is active (check for BLE log messages)

### Command Queue Still Overflowing
- Verify you're using the optimized fork (check YAML)
- Check that `throttle: 300ms` is NOT in light configs
- Monitor logs for command count with `grep -i "sending command"`
- Consider increasing `MIN_COMMAND_INTERVAL_MS` in fastcon_light.h

## Future Enhancements

1. **Custom Pairing Component** (`brmesh_pairing.h`):
   - Parse manufacturer data to extract device info
   - Auto-assign sequential light IDs
   - Store paired lights persistently
   - Export YAML configuration automatically

2. **UI Integration**:
   - Add toggle in web UI for optimized/standard mode
   - Real-time pairing UI with device discovery
   - Drag-and-drop light ordering

3. **Advanced Features**:
   - Scene activation without phone app
   - Group definitions from ESP32
   - Music reactive mode with UDP sync

## Related Files

- `esphome_generator.py`: YAML generation logic
- `brmesh_bridge.py`: Addon configuration
- `test_yaml_generation.py`: Test script
- Fork: https://github.com/tofuweasel/esphome-fastcon/tree/optimized
- Documentation: See fork's `OPTIMIZATION.md`

## References

- Original fork: https://github.com/scross01/esphome-fastcon
- Optimized fork: https://github.com/tofuweasel/esphome-fastcon/tree/optimized
- ESPHome: https://esphome.io
- BRMesh Protocol: See addon's protocol documentation
