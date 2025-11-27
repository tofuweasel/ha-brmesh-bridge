#!/usr/bin/env python3
"""
Scan for ALL BLE devices and show manufacturer data
Helps identify the correct manufacturer ID for BRMesh devices
"""

import asyncio
from bleak import BleakScanner
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

async def scan_all():
    """Scan for all BLE devices"""
    
    logger.info("=" * 70)
    logger.info("🔍 Scanning for ALL BLE devices...")
    logger.info("=" * 70)
    logger.info("Looking for any devices with manufacturer data")
    logger.info("Scan duration: 30 seconds")
    logger.info("")
    
    devices_found = {}
    
    def detection_callback(device, advertisement_data):
        mac = device.address
        
        if mac not in devices_found:
            devices_found[mac] = {
                'name': device.name or 'Unknown',
                'rssi': advertisement_data.rssi,
                'manufacturer_data': {},
                'service_uuids': []
            }
            
            logger.info(f"📡 Device: {mac}")
            logger.info(f"   Name: {device.name or 'Unknown'}")
            logger.info(f"   RSSI: {advertisement_data.rssi} dBm")
            
            if advertisement_data.manufacturer_data:
                for mfr_id, data in advertisement_data.manufacturer_data.items():
                    logger.info(f"   🏭 Manufacturer ID: 0x{mfr_id:04x} ({mfr_id} decimal)")
                    logger.info(f"      Data ({len(data)} bytes): {data.hex()}")
                    devices_found[mac]['manufacturer_data'][mfr_id] = data
            
            if advertisement_data.service_uuids:
                logger.info(f"   🔧 Services: {', '.join(advertisement_data.service_uuids)}")
                devices_found[mac]['service_uuids'] = advertisement_data.service_uuids
            
            if advertisement_data.service_data:
                for uuid, data in advertisement_data.service_data.items():
                    logger.info(f"   📦 Service Data ({uuid}): {data.hex()}")
            
            logger.info("")
    
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(30)
    await scanner.stop()
    
    logger.info("=" * 70)
    logger.info(f"📊 SUMMARY: Found {len(devices_found)} devices")
    logger.info("=" * 70)
    
    # Look for likely BRMesh candidates
    logger.info("")
    logger.info("🔍 Potential BRMesh devices (with manufacturer data):")
    for mac, info in devices_found.items():
        if info['manufacturer_data']:
            has_16_or_24 = any(len(data) in [16, 24] for data in info['manufacturer_data'].values())
            if has_16_or_24:
                logger.info(f"  ⭐ {mac} - {info['name']}")
                for mfr_id, data in info['manufacturer_data'].items():
                    logger.info(f"      Mfr 0x{mfr_id:04x}: {len(data)} bytes - {data.hex()}")

if __name__ == "__main__":
    try:
        asyncio.run(scan_all())
    except KeyboardInterrupt:
        logger.info("\n⚠️  Scan interrupted")
