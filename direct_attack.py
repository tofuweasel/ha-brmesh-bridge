"""
Direct attack - connect to known MAC address immediately
No scanning delay, just direct connection attempt
"""
import asyncio
from bleak import BleakClient

MESH_KEY = bytes.fromhex('30323336')
TARGET = '78:B6:FE:60:E5:74'

def xor_encrypt(key, data):
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])
    return bytes(result)

def generate_color_command(red, green, blue, white):
    header = bytes([0x06, 0x0c, 0x00, 0xff, 0xff, 0xff, 0xff])
    payload = bytes([red, green, blue, white, 0x00, 0x00, 0x00, 0x06])
    magic = bytes.fromhex('c47b365e')
    encrypted_header = xor_encrypt(magic, header)
    encrypted_payload = xor_encrypt(MESH_KEY, payload)
    return encrypted_header + encrypted_payload

async def direct_attack():
    print("="*70)
    print("⚡ DIRECT ATTACK - NO SCAN DELAY")
    print("="*70)
    print(f"\nTarget: {TARGET}")
    print(f"Mesh Key: {MESH_KEY.hex()}")
    print("\n🎮 CONTROL YOUR LIGHT WITH YOUR PHONE RIGHT NOW!")
    print("   (This will wake it up and make it connectable)")
    print("\nWaiting 3 seconds for you to tap the phone...")
    
    await asyncio.sleep(3)
    
    print("\n🔌 Attempting direct connection...")
    
    try:
        # Direct connection with longer timeout
        async with BleakClient(TARGET, timeout=20) as client:
            print("✅ CONNECTED!")
            
            # Enumerate writable characteristics
            print("\n📝 Finding writable characteristics...")
            write_chars = []
            
            for service in client.services:
                for char in service.characteristics:
                    props_list = char.properties
                    if "write" in props_list or "write-without-response" in props_list:
                        write_chars.append((char.uuid, service.uuid, props_list))
                        print(f"   Found: {char.uuid}")
                        print(f"      Service: {service.uuid}")
                        print(f"      Props: {', '.join(props_list)}")
            
            if not write_chars:
                print("\n❌ No writable characteristics found!")
                return
            
            # Generate attack commands
            red = generate_color_command(255, 0, 0, 0)
            blue = generate_color_command(0, 0, 255, 0)
            white = generate_color_command(0, 0, 0, 255)
            
            print(f"\n{'='*70}")
            print("🎨 SENDING COLOR ATTACK SEQUENCE")
            print(f"{'='*70}")
            
            # Try EACH writable characteristic
            for char_uuid, svc_uuid, props in write_chars:
                print(f"\n🎯 Trying characteristic: {char_uuid}")
                
                use_response = "write-without-response" not in props
                
                try:
                    print(f"   📤 RED command...")
                    await client.write_gatt_char(char_uuid, red, response=use_response)
                    print(f"      ✅ Sent!")
                    await asyncio.sleep(1.5)
                    
                    print(f"   📤 BLUE command...")
                    await client.write_gatt_char(char_uuid, blue, response=use_response)
                    print(f"      ✅ Sent!")
                    await asyncio.sleep(1.5)
                    
                    print(f"   📤 WHITE command...")
                    await client.write_gatt_char(char_uuid, white, response=use_response)
                    print(f"      ✅ Sent!")
                    
                    print(f"\n   ✅ SUCCESS ON {char_uuid}!")
                    print(f"   💡 Did your light change colors?")
                    
                except Exception as e:
                    print(f"      ❌ Failed: {e}")
                    continue
            
            print(f"\n{'='*70}")
            print("✅ ATTACK SEQUENCE COMPLETE")
            print(f"{'='*70}")
            
    except Exception as e:
        print(f"\n❌ Connection failed: {e}")
        print("\n💡 Try running this again WHILE pressing buttons in your phone app")

if __name__ == "__main__":
    asyncio.run(direct_attack())
