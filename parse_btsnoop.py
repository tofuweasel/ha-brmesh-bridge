#!/usr/bin/env python3
"""
Parse btsnoop_hci.log to extract BRMesh device MAC addresses and advertisement data
"""

import struct
import sys

def parse_btsnoop(filename):
    """Parse Android btsnoop_hci.log format"""
    
    devices = {}
    packet_count = 0
    
    with open(filename, 'rb') as f:
        # Read file header
        # Format: "btsnoop\0" + version (4 bytes) + data link type (4 bytes)
        header = f.read(16)
        if not header.startswith(b'btsnoop\x00'):
            print("❌ Not a valid btsnoop file!")
            return devices
        
        print(f"✅ Valid btsnoop file")
        print(f"   Version: {struct.unpack('>I', header[8:12])[0]}")
        print()
        
        # Read packet records
        while True:
            # Packet record header: 24 bytes
            # - Original length (4 bytes)
            # - Included length (4 bytes)
            # - Flags (4 bytes)
            # - Cumulative drops (4 bytes)
            # - Timestamp (8 bytes)
            record_header = f.read(24)
            
            if len(record_header) < 24:
                break  # End of file
            
            orig_len, incl_len, flags, drops = struct.unpack('>IIII', record_header[:16])
            timestamp_us = struct.unpack('>Q', record_header[16:24])[0]
            
            # Read packet data
            packet_data = f.read(incl_len)
            if len(packet_data) < incl_len:
                break
            
            packet_count += 1
            
            # Parse HCI packets
            # We're looking for: HCI Event (0x04), LE Meta Event (0x3E), Advertising Report (0x02)
            if len(packet_data) > 0 and packet_data[0] == 0x04:  # HCI Event
                if len(packet_data) > 2 and packet_data[1] == 0x3E:  # LE Meta Event
                    if len(packet_data) > 3 and packet_data[3] == 0x02:  # LE Advertising Report
                        # Parse LE Advertising Report
                        try:
                            offset = 4  # Start of report data
                            num_reports = packet_data[offset]
                            offset += 1
                            
                            for _ in range(num_reports):
                                if offset + 8 > len(packet_data):
                                    break
                                
                                event_type = packet_data[offset]
                                addr_type = packet_data[offset + 1]
                                # MAC address (6 bytes, little-endian)
                                mac_bytes = packet_data[offset + 2:offset + 8]
                                mac = ':'.join(f'{b:02X}' for b in reversed(mac_bytes))
                                offset += 8
                                
                                # AD data length
                                if offset >= len(packet_data):
                                    break
                                ad_len = packet_data[offset]
                                offset += 1
                                
                                # AD data
                                if offset + ad_len > len(packet_data):
                                    break
                                ad_data = packet_data[offset:offset + ad_len]
                                offset += ad_len
                                
                                # RSSI
                                if offset >= len(packet_data):
                                    break
                                rssi = struct.unpack('b', packet_data[offset:offset + 1])[0]
                                offset += 1
                                
                                # Track device
                                if mac not in devices:
                                    devices[mac] = {
                                        'packets': 0,
                                        'rssi': rssi,
                                        'mfr_data': []
                                    }
                                devices[mac]['packets'] += 1
                                devices[mac]['rssi'] = rssi
                                
                                # Parse AD structures
                                i = 0
                                while i < len(ad_data):
                                    if i >= len(ad_data):
                                        break
                                    length = ad_data[i]
                                    if length == 0 or i + length + 1 > len(ad_data):
                                        break
                                    
                                    ad_type = ad_data[i + 1]
                                    ad_value = ad_data[i + 2:i + 1 + length]
                                    
                                    # 0xFF = Manufacturer Specific Data
                                    if ad_type == 0xFF and len(ad_value) >= 2:
                                        mfr_id = struct.unpack('<H', ad_value[0:2])[0]
                                        mfr_payload = ad_value[2:]
                                        
                                        # BRMesh uses 16 or 24 byte manufacturer data
                                        if len(mfr_payload) in [16, 24]:
                                            devices[mac]['mfr_data'].append({
                                                'mfr_id': mfr_id,
                                                'data': mfr_payload.hex()
                                            })
                                    
                                    i += length + 1
                        except Exception as e:
                            pass
    
    print(f"📊 Parsed {packet_count} HCI packets")
    print(f"📡 Found {len(devices)} unique BLE devices")
    print()
    
    return devices


if __name__ == "__main__":
    filename = '../../../fresh_attack_btsnoop.log'
    
    devices = parse_btsnoop(filename)
    
    # Filter for BRMesh devices (those with 16 or 24 byte manufacturer data)
    brmesh_devices = {mac: info for mac, info in devices.items() if info['mfr_data']}
    
    print("=" * 70)
    print(f"🎯 BRMesh Devices Found: {len(brmesh_devices)}")
    print("=" * 70)
    
    if brmesh_devices:
        for mac, info in brmesh_devices.items():
            print(f"\n📍 MAC: {mac}")
            print(f"   RSSI: {info['rssi']} dBm")
            print(f"   Packets captured: {info['packets']}")
            
            # Show unique manufacturer data
            unique_data = {}
            for mfr in info['mfr_data']:
                key = (mfr['mfr_id'], len(mfr['data'])//2)
                if key not in unique_data:
                    unique_data[key] = mfr['data']
            
            for (mfr_id, data_len), data_hex in unique_data.items():
                print(f"\n   Manufacturer ID: 0x{mfr_id:04x}")
                print(f"   Data length: {data_len} bytes")
                print(f"   Data: {data_hex}")
                
                # Decode if it's a pairing packet (16 bytes)
                if data_len == 16:
                    data_bytes = bytes.fromhex(data_hex)
                    print(f"   🔓 PAIRING PACKET!")
                    print(f"      MAC in packet: {':'.join(f'{b:02X}' for b in data_bytes[0:6])}")
                    print(f"      Address: {data_bytes[6]}")
                    print(f"      Constant: {data_bytes[7]}")
                    print(f"      🔑 MESH KEY: {data_bytes[8:12].hex()}")
                    print(f"         ASCII: '{data_bytes[8:12].decode('ascii', errors='replace')}'")
        
        print("\n" + "=" * 70)
        print("✅ Found your BRMesh lights!")
        print("   These are the MAC addresses to target from your computer")
        print("=" * 70)
    else:
        print("❌ No BRMesh devices found in capture")
        print("\nThis could mean:")
        print("  • The lights didn't broadcast during capture")
        print("  • Capture happened too late (after commands finished)")
        print("  • Different manufacturer data format")
