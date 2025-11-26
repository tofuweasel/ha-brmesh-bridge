# How to Fork and Apply the Optimized fastcon Component

## Step 1: Fork the Repository

1. Go to https://github.com/scross01/esphome-fastcon
2. Click the **Fork** button in the top right
3. This creates `https://github.com/YOUR_USERNAME/esphome-fastcon`

## Step 2: Clone Your Fork Locally

```powershell
cd C:\Profiles\crval\Nextcloud\Projects
git clone https://github.com/YOUR_USERNAME/esphome-fastcon.git
cd esphome-fastcon
```

## Step 3: Create Optimized Branch

```powershell
# Create and switch to new branch
git checkout -b optimized

# Verify you're on the new branch
git branch
```

## Step 4: Replace the Light Component Files

Copy the optimized files from the addon directory:

```powershell
# From the esphome-fastcon directory
copy ..\HomeAssistant\addons\brmesh-bridge\esphome\fastcon_light_optimized.h components\fastcon\fastcon_light.h
copy ..\HomeAssistant\addons\brmesh-bridge\esphome\fastcon_light_optimized.cpp components\fastcon\fastcon_light.cpp
```

Or manually:
1. Open `components/fastcon/fastcon_light.h`
2. Replace entire contents with `fastcon_light_optimized.h`
3. Open `components/fastcon/fastcon_light.cpp`
4. Replace entire contents with `fastcon_light_optimized.cpp`

## Step 5: Commit and Push

```powershell
# Stage the changes
git add components/fastcon/fastcon_light.h
git add components/fastcon/fastcon_light.cpp

# Commit with descriptive message
git commit -m "Optimize light component with command deduplication and debouncing

- Add per-light state tracking to prevent duplicate commands
- Implement 100ms debouncing to wait for state changes to settle
- Enforce 300ms minimum interval between commands
- Skip sending identical consecutive commands to same light

This reduces BLE command spam by 66% when controlling multiple lights
or making rapid state changes (e.g., brightness slider, color changes).

Fixes issue where turning off 3 lights sends 9 commands instead of 3."

# Push to GitHub
git push origin optimized
```

## Step 6: Update ESPHome YAML

Edit `brmesh-bridge-optimized.yaml` and change:

```yaml
external_components:
  - source: github://YOUR_USERNAME/esphome-fastcon@optimized
    components: [fastcon]
    refresh: 0s  # Force refresh during development
```

Replace `YOUR_USERNAME` with your actual GitHub username.

## Step 7: Test the Configuration

```powershell
# Validate the YAML
esphome config brmesh-bridge-optimized.yaml

# Compile and flash
esphome run brmesh-bridge-optimized.yaml
```

## Step 8: Monitor Logs

After flashing, watch the logs to verify the optimization is working:

```powershell
esphome logs brmesh-bridge-optimized.yaml
```

Look for log messages like:
```
[D][fastcon.light:XX] Sending debounced command for light 1 (delayed 102ms)
[V][fastcon.light:XX] Skipping duplicate command for light 1
```

## Step 9: Test Performance

### Test 1: Turn off 3 lights sequentially
```yaml
# Home Assistant Developer Tools > Services
service: light.turn_off
target:
  entity_id:
    - light.living_room_light_1
    - light.living_room_light_2
    - light.bedroom_light
```

**Expected**: 3 BLE commands sent (check logs)  
**Before optimization**: 9 BLE commands would be sent

### Test 2: Drag brightness slider
Move the brightness slider rapidly from 0 to 255.

**Expected**: 1-2 BLE commands sent (debounced)  
**Before optimization**: 10+ BLE commands would be sent

## Step 10: (Optional) Submit PR to Upstream

If the optimization works well, consider submitting a Pull Request to the original repository:

1. Go to https://github.com/scross01/esphome-fastcon
2. Click **Pull requests** > **New pull request**
3. Click **compare across forks**
4. Select your fork and the `optimized` branch
5. Add title: "Fix command spam with deduplication and debouncing"
6. Reference the COMMAND_OPTIMIZATION.md document
7. Submit the PR

## Troubleshooting

### "Couldn't find source" error
- Verify your GitHub username is correct in the YAML
- Verify the branch name is `optimized`
- Try setting `refresh: 1d` instead of `0s` after first successful compile

### Compilation errors
- Ensure you replaced BOTH `.h` and `.cpp` files
- Check that the files are valid C++ (no YAML mixing)
- Verify the optimized files are in the correct location

### No performance improvement
- Check ESPHome logs for "debounced" or "duplicate" messages
- Verify you're using the forked version (check compile output)
- Ensure lights are defined with `controller_id: fastcon_controller`

## Configuration Parameters

The optimized component uses these hardcoded timing parameters:

```cpp
static const uint32_t DEBOUNCE_MS = 100;      // Wait 100ms after last state change
static const uint32_t MIN_INTERVAL_MS = 300;   // Minimum 300ms between commands
```

To adjust these, edit `components/fastcon/fastcon_light.h` in your fork:

```cpp
// Faster response (may send more commands)
static const uint32_t DEBOUNCE_MS = 50;       // 50ms debounce
static const uint32_t MIN_INTERVAL_MS = 200;  // 200ms interval

// Fewer commands (slower response)
static const uint32_t DEBOUNCE_MS = 150;      // 150ms debounce
static const uint32_t MIN_INTERVAL_MS = 400;  // 400ms interval
```

Then commit and push the changes.

## Success Criteria

✅ ESPHome compiles without errors  
✅ Lights respond to Home Assistant commands  
✅ Turning off 3 lights sends only 3 BLE commands (check logs)  
✅ Brightness slider sends 1-2 commands instead of 10+  
✅ No "queue full" warnings in logs  
✅ Response time feels snappy (not sluggish)

## Need Help?

Check the full documentation in `COMMAND_OPTIMIZATION.md` for:
- Detailed explanation of the problem
- Performance benchmarks
- Alternative solutions
- Advanced tuning options
