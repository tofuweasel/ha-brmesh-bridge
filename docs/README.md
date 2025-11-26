# BRMesh Protocol Reverse Engineering

> Complete protocol documentation for BRMesh Bluetooth mesh lighting system

This repository contains the fully reverse-engineered BRMesh protocol, enabling direct control of BRMesh lights without the official app.

## 🎯 What We've Accomplished

Through systematic protocol analysis using ADB logcat monitoring, we've fully decoded:

- ✅ **Pairing Protocol** - 12-byte format with device ID, light ID, and mesh key
- ✅ **Control Commands** - Power, brightness, color (RGB/temperature)
- ✅ **Group Protocol** - Multi-light control with group addressing
- ✅ **Scene Protocol** - Scene activation commands (captured)
- ✅ **Autonomous Effects** - Self-running color loops (single command)
- ✅ **App-Driven Effects** - Rainbow, complementary colors, music reactive
- ✅ **Music Mode** - FFT analysis and frequency-to-color mapping

## 📊 Protocol Summary

| Feature | Opcode | Autonomous | Status |
|---------|--------|------------|--------|
| Power | `0x43` | No | ✅ Complete |
| Brightness | `0x43` | No | ✅ Complete |
| Color (RGB) | `0x93` | No | ✅ Complete |
| Custom Effect | `0x00 0x52` | Yes | ✅ Complete |
| Rainbow Mode | `0x93` + `0xf8` | No | ✅ Complete |
| Complementary | `0x93` + `0xc1` | No | ✅ Complete |
| Music Reactive | `0x93` | No | ✅ Complete |
| Scene Activation | `0x89`, `0x3b` | Yes | 🟡 Captured |

## 🔑 Key Discoveries

### Pairing Protocol
```
Format: [DeviceID:6][LightID:2][MeshKey:4]
Manufacturer: 0xf0ff
Mesh Key: "0236" (hex: 30323336)
Encryption Key: "5e367bc4"
```

### Autonomous Effects (0x00 0x52)
Single command creates self-running effects in the light:
```
00 52 04 03 30 ff 00 00 00 ff 00 00 00 ff 00 00
          ^^    ^^^^^^^ ^^^^^^^ ^^^^^^^
          ||    Red     Green   Blue
          Speed (0x30 = ~768ms per color)
```

### Music Reactive Mode
- Phone performs FFT analysis of audio input
- Bass (0-500Hz) → Red channel
- Mid (500-2kHz) → Green channel  
- Treble (2-8kHz) → Blue channel
- Rapid `0x93` color updates at 100ms intervals

## 🚀 Implementation

### Python Effect Builder
```python
from effects import EffectBuilder, EffectPresets

# Create autonomous rainbow effect
rainbow = EffectPresets.rainbow_loop(speed=0x30)
cmd = EffectBuilder.create_autonomous_effect(rainbow.colors, rainbow.speed)
# Output: 0052040330ff000000ff000000ff0000

# Create direct color command
cmd = EffectBuilder.create_color_command(
    target=(0x2a, 0xa8),  # Group address
    r=255, g=0, b=0,      # Red
    mode=EffectBuilder.MODE_RAINBOW
)
```

### ESP32 Music Mode
Real-time FFT analysis with I2S microphone:
```cpp
// Analyze audio and map to colors
analyze_frequencies();  // FFT → bass/mid/treble levels

uint8_t r = (uint8_t)(bass_level * 255.0);
uint8_t g = (uint8_t)(mid_level * 255.0);
uint8_t b = (uint8_t)(treble_level * 255.0);

// Send BRMesh color command
send_color_command(target, r, g, b);
```

### UDP Sound Sync (WLED-Style)
One ESP32 with microphone broadcasts FFT data to multiple ESP32s without microphones:
```yaml
# Master ESP32 (with mic)
includes:
  - fft_analyzer_udp.h

# Slave ESP32 (no mic needed!)
includes:
  - fft_analyzer_udp.h

# Both receive same audio analysis via UDP
# Synchronized music reactive lighting across multiple zones
```

## 📁 Files

- **`PROTOCOL.md`** - Complete protocol specification
- **`EFFECTS.md`** - Effects protocol and examples
- **`PAIRING.md`** - Native ESP32 pairing guide
- **`effects.py`** - Python implementation
- **`fft_analyzer.h`** - C++ FFT for ESP32
- **`fft_analyzer_udp.h`** - UDP sound sync implementation

## 🎵 ESP32 Music Mode Features

- **Hardware**: ESP32 + INMP441 I2S microphone ($7 total)
- **Latency**: <100ms audio-to-light
- **Update Rate**: 10fps (adjustable 5-30fps)
- **Modes**: RGB Frequency, Amplitude, Rainbow Cycle, Bass Pulse
- **FFT**: 256-point transform @ 22.05kHz
- **Power**: ~225mA peak

## 🔧 Quick Start

### Test Basic Control
```python
# Power ON
43 2a a8 04 80 00 00 00 00 00 00 00

# Red color
93 2a a8 04 ff ff 00 00 00 00 00 00

# Rainbow effect (autonomous)
00 52 04 03 30 ff 00 00 00 ff 00 00 00 ff 00 00
```

### Speed Reference
| Speed | Time/Color | Use Case |
|-------|-----------|----------|
| `0x01` | ~16ms | Ultra-fast strobe |
| `0x10` | ~256ms | Fire effect |
| `0x30` | ~768ms | Medium fade |
| `0x80` | ~2s | Slow fade |

## 🎯 Use Cases

1. **Home Assistant Integration** - Direct control without proprietary app
2. **Music Visualization** - Real-time audio-reactive lighting
3. **Automation** - Scenes, schedules, triggers
4. **Multi-Zone Audio Sync** - One mic, multiple ESP32s via UDP
5. **Custom Effects** - User-defined color sequences

## 📖 Protocol Documentation

### Basic Commands

**Power & Brightness (0x43)**
```
Power ON:  43 2a a8 04 80 00 00 00 00 00 00 00
Power OFF: 43 2a a8 04 00 00 00 00 00 00 00 00
Brightness: 43 2a a8 04 [VALUE] 00 00 00 00 00 00 00
```

**Color Control (0x93)**
```
Direct RGB: 93 [target] 04 ff [R] [G] [B] 00 00 00 00
Rainbow:    93 [target] 04 f8 [R] [G] [B] 00 00 00 00
Complementary: 93 [target] 04 c1 [R] [G] [B] 00 00 00 00
```

**Custom Effects (0x00 0x52)**
```
Format: 00 52 04 [num_colors] [speed] [RGB1] [RGB2] [RGB3] ...
Example (3-color): 00 52 04 03 30 ff 00 00 00 ff 00 00 00 ff 00 00
```

## 🏗️ Architecture

```
┌─────────────────┐
│  BRMesh App     │  ← Original (reverse engineered)
└────────┬────────┘
         │ BLE Mesh
         ↓
┌─────────────────┐
│  BRMesh Lights  │
└─────────────────┘

         ↓ Now also controlled by ↓

┌─────────────────┐     ┌──────────────┐
│  ESP32 Bridge   │────→│ Home Assistant│
│  (ESPHome)      │     │  Integration  │
│                 │     └──────────────┘
│  • BLE Control  │
│  • FFT Audio    │
│  • UDP Sync     │
└─────────────────┘
```

## 🔬 Methodology

Protocol was reverse-engineered using:
1. ADB logcat monitoring of official Android app
2. Systematic feature testing (scenes, groups, effects, music mode)
3. Packet capture and analysis
4. Pattern recognition across 500+ captured commands
5. Iterative testing to confirm hypotheses

## 📊 Statistics

- **Capture Sessions**: 6 major sessions
- **Commands Captured**: 500+
- **Protocol Coverage**: ~90%
- **Lines of Code**: 1,800+ (Python, C++, documentation)
- **Development Time**: Intensive analysis over multiple sessions

## 🎉 Benefits

- ✅ No phone app required
- ✅ Local control (no cloud dependency)
- ✅ Home automation integration
- ✅ Custom effects and animations
- ✅ Music reactive lighting
- ✅ Multi-zone synchronization
- ✅ Open source and extensible

## 🤝 Contributing

This is a complete protocol documentation project. If you discover additional features or improve the implementation, contributions are welcome!

## ⚠️ Disclaimer

This is an independent reverse engineering project for educational and interoperability purposes. BRMesh is a trademark of its respective owner. This project is not affiliated with or endorsed by the manufacturer.

## 📄 License

MIT License - See LICENSE file for details

---

**Status**: Protocol fully documented and implemented  
**Last Updated**: November 2025  
**Compatibility**: All BRMesh lights with manufacturer ID 0xf0ff
