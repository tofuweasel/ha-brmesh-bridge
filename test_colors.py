#!/usr/bin/env python3
"""
Send visible color commands to test if device responds
"""

import asyncio
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'rootfs', 'app'))
from brmesh_control import create_control_command
from bleak import BleakClient

MESH_KEY = bytes.fromhex('30323336')
TARGET = '10:52:1C:B9:57:E2'

async def send_color_sequence():
    print("=" * 70)
    print("🎨 Sending Color Sequence Test")
    print("=" * 70)
    print(f"Target device: {TARGET}")
    print(f"Mesh key: {MESH_KEY.hex()}")
    print("")
    print("This will send: RED → BLUE → WHITE commands")
    print("Watch your lights for any color changes!")
    print("")
    
    try:
        async with BleakClient(TARGET, timeout=15) as client:
            print(f"✅ Connected to {TARGET}")
            
            char = '0000ff53-0000-1000-8000-00805f9b34fb'
            
            # Command 1: BRIGHT RED
            print("\n🔴 Sending RED command...")
            payload = bytes([0x01, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00] + [0x00] * 13)
            cmd = create_control_command(address=0xFF, cmd_type=1, payload=payload, mesh_key=MESH_KEY, seq=1)
            print(f"   Command: {cmd.hex()}")
            await client.write_gatt_char(char, cmd, response=False)
            print("   ✅ Sent!")
            await asyncio.sleep(3)
            
            # Command 2: BRIGHT BLUE
            print("\n🔵 Sending BLUE command...")
            payload = bytes([0x01, 0xFF, 0x00, 0x00, 0xFF, 0x00, 0x00] + [0x00] * 13)
            cmd = create_control_command(address=0xFF, cmd_type=1, payload=payload, mesh_key=MESH_KEY, seq=2)
            print(f"   Command: {cmd.hex()}")
            await client.write_gatt_char(char, cmd, response=False)
            print("   ✅ Sent!")
            await asyncio.sleep(3)
            
            # Command 3: WHITE
            print("\n⚪ Sending WHITE command...")
            payload = bytes([0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00] + [0x00] * 13)
            cmd = create_control_command(address=0xFF, cmd_type=1, payload=payload, mesh_key=MESH_KEY, seq=3)
            print(f"   Command: {cmd.hex()}")
            await client.write_gatt_char(char, cmd, response=False)
            print("   ✅ Sent!")
            
            print("\n" + "=" * 70)
            print("Did your lights change color?")
            print("=" * 70)
            print("")
            print("If YES: Security vulnerability confirmed! ✅")
            print("If NO:  Possible reasons:")
            print("  • Wrong BLE characteristic (try 0xff54 instead)")
            print("  • Device is not a BRMesh light")
            print("  • Different protocol version")
            print("  • Commands need different format")
            
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(send_color_sequence())
