"""
Enumerate all GATT services and characteristics from BRMesh light
"""
import asyncio
from bleak import BleakScanner, BleakClient

async def find_and_enumerate():
    print("Scanning for BRMesh lights...")
    devices = await BleakScanner.discover(timeout=8, return_adv=True)
    
    target = None
    for addr, (device, adv_data) in devices.items():
        if adv_data.manufacturer_data:
            for mfr_id, data in adv_data.manufacturer_data.items():
                if mfr_id == 0xfff0 and len(data) == 24:
                    target = addr
                    print(f"\n✅ Found BRMesh light: {addr}")
                    break
        if target:
            break
    
    if not target:
        print("❌ No BRMesh lights found!")
        return
    
    print(f"\nConnecting to {target}...")
    async with BleakClient(target, timeout=15) as client:
        print("✅ Connected!\n")
        print("="*70)
        print("GATT SERVICES AND CHARACTERISTICS")
        print("="*70)
        
        for service in client.services:
            print(f"\n🔷 Service: {service.uuid}")
            print(f"   Description: {service.description}")
            
            for char in service.characteristics:
                props = ", ".join(char.properties)
                print(f"\n   📝 Characteristic: {char.uuid}")
                print(f"      Description: {char.description}")
                print(f"      Properties: {props}")
                print(f"      Handle: {char.handle}")
                
                # Try to read if readable
                if "read" in char.properties:
                    try:
                        value = await client.read_gatt_char(char.uuid)
                        print(f"      Value: {value.hex() if value else 'empty'}")
                        try:
                            print(f"      ASCII: {value.decode('utf-8', errors='ignore')}")
                        except:
                            pass
                    except Exception as e:
                        print(f"      (Could not read: {e})")

if __name__ == "__main__":
    asyncio.run(find_and_enumerate())
