#!/usr/bin/env python3
"""
Scan for devices broadcasting 24-byte manufacturer data (BRMesh signature)
"""

import asyncio
from bleak import BleakScanner

async def scan_for_manufacturer_data():
    print("=" * 70)
    print("🔍 Scanning for BRMesh Lights by Manufacturer Data")
    print("=" * 70)
    print("Looking for devices broadcasting 24-byte manufacturer data...")
    print("(This is the primary way BRMesh lights advertise)")
    print("")
    
    devices_with_24byte = []
    all_devices = {}
    
    def callback(device, ad_data):
        mac = device.address.upper()
        
        if mac not in all_devices:
            all_devices[mac] = {
                'name': device.name or 'Unknown',
                'rssi': ad_data.rssi,
                'manufacturer_data': {}
            }
        
        # Check manufacturer data
        if ad_data.manufacturer_data:
            for mfr_id, data in ad_data.manufacturer_data.items():
                all_devices[mac]['manufacturer_data'][mfr_id] = data
                
                # BRMesh lights broadcast 24-byte manufacturer data
                if len(data) == 24:
                    if mac not in [d['mac'] for d in devices_with_24byte]:
                        devices_with_24byte.append({
                            'mac': mac,
                            'name': device.name or 'Unknown',
                            'rssi': ad_data.rssi,
                            'mfr_id': mfr_id,
                            'data': data
                        })
                        print(f"⭐ Found 24-byte manufacturer data!")
                        print(f"   MAC: {mac}")
                        print(f"   Name: {device.name or 'Unknown'}")
                        print(f"   RSSI: {ad_data.rssi} dBm")
                        print(f"   Manufacturer ID: 0x{mfr_id:04x} ({mfr_id})")
                        print(f"   Data: {data.hex()}")
                        print("")
    
    scanner = BleakScanner(detection_callback=callback)
    await scanner.start()
    await asyncio.sleep(20)
    await scanner.stop()
    
    print("=" * 70)
    print(f"RESULTS: Found {len(devices_with_24byte)} device(s) with 24-byte manufacturer data")
    print("=" * 70)
    
    if devices_with_24byte:
        print("\n✅ These are likely your BRMesh lights!")
        for dev in devices_with_24byte:
            print(f"\n   MAC: {dev['mac']}")
            print(f"   Name: {dev['name']}")
            print(f"   RSSI: {dev['rssi']} dBm")
            print(f"   Mfr ID: 0x{dev['mfr_id']:04x}")
    else:
        print("\n❌ No devices found with 24-byte manufacturer data")
        print("\nPossible issues:")
        print("  • Lights are actually off or in sleep mode")
        print("  • Lights are too far away (weak signal)")
        print("  • Windows Bluetooth isn't capturing manufacturer data")
        print("\nAll devices found:")
        for mac, info in list(all_devices.items())[:10]:
            mfr_info = ""
            if info['manufacturer_data']:
                for mid, mdata in info['manufacturer_data'].items():
                    mfr_info = f" [Mfr 0x{mid:04x}: {len(mdata)} bytes]"
                    break
            print(f"   {mac} - {info['name']} (RSSI: {info['rssi']}){mfr_info}")

if __name__ == "__main__":
    asyncio.run(scan_for_manufacturer_data())
