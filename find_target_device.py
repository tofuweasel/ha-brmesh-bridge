#!/usr/bin/env python3
"""
Extended scan to find specific BRMesh device
"""

import asyncio
from bleak import BleakScanner

TARGET_MAC = "4E:5F:6B:1C:34:8E"  # Device with a88b in pairing data

async def scan():
    print("=" * 70)
    print("🔍 Extended BLE Device Scan")
    print("=" * 70)
    print(f"Looking for target MAC: {TARGET_MAC}")
    print("Scanning for 20 seconds...")
    print("")
    
    devices = {}
    target_found = False
    
    def callback(device, ad_data):
        nonlocal target_found
        mac = device.address.upper()
        
        if mac not in devices:
            devices[mac] = {
                'name': device.name or 'Unknown',
                'rssi': ad_data.rssi,
                'manufacturer_data': ad_data.manufacturer_data,
                'service_uuids': ad_data.service_uuids or []
            }
            
            is_target = (mac == TARGET_MAC.upper())
            marker = "⭐ TARGET!" if is_target else ""
            
            print(f"{mac} - {device.name or 'Unknown'} (RSSI: {ad_data.rssi}) {marker}")
            
            if is_target:
                target_found = True
                if ad_data.manufacturer_data:
                    print(f"   Manufacturer data:")
                    for mfr_id, data in ad_data.manufacturer_data.items():
                        print(f"      0x{mfr_id:04x}: {data.hex()}")
                if ad_data.service_uuids:
                    print(f"   Services: {', '.join(ad_data.service_uuids)}")
    
    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(20)
    await scanner.stop()
    
    print("")
    print("=" * 70)
    print(f"Total devices found: {len(devices)}")
    print("=" * 70)
    
    if target_found:
        print(f"✅ Target device {TARGET_MAC} FOUND!")
        print("")
        print("Ready to send control command.")
    else:
        print(f"❌ Target device {TARGET_MAC} NOT found")
        print("")
        print("Possible reasons:")
        print("  • Device is powered off")
        print("  • Device is out of BLE range (>30m)")
        print("  • Device is in sleep mode")
        print("  • Device MAC has changed")
        print("")
        print("Devices with 'fff' service UUIDs (likely BRMesh):")
        for mac, info in devices.items():
            if any('fff' in uuid.lower() for uuid in info['service_uuids']):
                print(f"   {mac} - {info['name']} (RSSI: {info['rssi']})")

if __name__ == "__main__":
    asyncio.run(scan())
