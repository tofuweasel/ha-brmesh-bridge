"""
Wake up BRMesh lights by broadcasting mesh packets
Then enumerate GATT characteristics once awake
"""
import asyncio
from bleak import BleakScanner, BleakClient
import struct

MESH_KEY = bytes.fromhex('30323336')

def xor_encrypt(key, data):
    """XOR encryption with repeating key"""
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])
    return bytes(result)

def create_broadcast_packet():
    """Create a BRMesh broadcast packet (like status query)"""
    # Header: opcode=0x06, length=0x0c, padding
    header = bytes([0x06, 0x0c, 0x00, 0xff, 0xff, 0xff, 0xff])
    
    # Payload: query status command
    # This should trigger lights to respond/wake up
    payload = bytes([0xff, 0xff, 0xff, 0x00, 0x00, 0x00, 0x00, 0x01])
    
    # Encrypt header with magic constant
    magic = bytes.fromhex('c47b365e')
    encrypted_header = xor_encrypt(magic, header)
    
    # Encrypt payload with mesh key
    encrypted_payload = xor_encrypt(MESH_KEY, payload)
    
    return encrypted_header + encrypted_payload

async def broadcast_wake_packets():
    """Broadcast several wake-up packets"""
    print("="*70)
    print("📡 BROADCASTING MESH WAKE-UP PACKETS")
    print("="*70)
    print(f"Using mesh key: {MESH_KEY.hex()}")
    
    packet = create_broadcast_packet()
    print(f"Broadcast packet: {packet.hex()}")
    print("\nNote: Windows BLE doesn't support advertising, but scanning will")
    print("trigger the lights to stay awake if they detect scan activity...")
    print("\nScanning continuously to wake lights...")
    
    # Continuous scanning keeps BLE active and may wake devices
    for i in range(3):
        print(f"\n🔍 Scan attempt {i+1}/3...")
        devices = await BleakScanner.discover(timeout=5, return_adv=True)
        
        found = []
        for addr, (device, adv_data) in devices.items():
            if adv_data.manufacturer_data:
                for mfr_id, data in adv_data.manufacturer_data.items():
                    if mfr_id == 0xfff0 and len(data) == 24:
                        found.append(addr)
                        print(f"   ✅ Found BRMesh light: {addr} (RSSI: {adv_data.rssi} dBm)")
        
        if found:
            print(f"\n🎯 Found {len(found)} light(s)! Attempting connection...")
            return found[0]
    
    print("\n❌ No lights found after 3 scan attempts")
    return None

async def enumerate_characteristics(target):
    """Connect and enumerate all GATT characteristics"""
    print("\n" + "="*70)
    print(f"🔌 CONNECTING TO: {target}")
    print("="*70)
    
    try:
        async with BleakClient(target, timeout=15) as client:
            print("✅ Connected!\n")
            
            write_chars = []
            
            for service in client.services:
                print(f"\n🔷 Service: {service.uuid}")
                print(f"   Description: {service.description}")
                
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    print(f"\n   📝 Char: {char.uuid}")
                    print(f"      Desc: {char.description}")
                    print(f"      Props: {props}")
                    print(f"      Handle: {char.handle}")
                    
                    # Track writable characteristics
                    if "write" in char.properties or "write-without-response" in char.properties:
                        write_chars.append((char.uuid, char.description, props))
                        print(f"      ⭐ WRITABLE!")
                    
                    # Try to read if readable
                    if "read" in char.properties:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            hex_val = value.hex() if value else 'empty'
                            print(f"      Value: {hex_val}")
                            try:
                                ascii_val = value.decode('utf-8', errors='ignore')
                                if ascii_val.isprintable():
                                    print(f"      ASCII: {ascii_val}")
                            except:
                                pass
                        except Exception as e:
                            print(f"      (Read failed: {e})")
            
            print("\n" + "="*70)
            print("📝 WRITABLE CHARACTERISTICS SUMMARY")
            print("="*70)
            for uuid, desc, props in write_chars:
                print(f"\n✅ {uuid}")
                print(f"   Description: {desc}")
                print(f"   Properties: {props}")
            
            return write_chars
            
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        return []

async def main():
    print("\n" + "="*70)
    print("🔓 BRMESH GATT ENUMERATION")
    print("="*70)
    print("\nThis will:")
    print("1. Scan aggressively to wake up BRMesh lights")
    print("2. Connect to discovered light")
    print("3. Enumerate all GATT services and characteristics")
    print("4. Identify the correct write characteristic for commands")
    print("="*70)
    
    target = await broadcast_wake_packets()
    
    if target:
        chars = await enumerate_characteristics(target)
        
        if chars:
            print("\n" + "="*70)
            print("✅ SUCCESS - Found writable characteristics!")
            print("="*70)
    else:
        print("\n💡 No lights found. Make sure lights are powered on.")

if __name__ == "__main__":
    asyncio.run(main())
