#!/usr/bin/env python3
"""
Analyze captured BRMesh advertisements to extract mesh key
Uses your existing brmesh_ads.txt capture file
"""

import sys
import os

# Add path for our protocol modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'rootfs', 'app'))
from brmesh_control import decode_control_command

def analyze_capture_file(filename='brmesh_ads.txt'):
    """Analyze captured BLE advertisements"""
    
    print("=" * 70)
    print("🔍 BRMesh Capture File Analysis")
    print("=" * 70)
    print(f"Reading: {filename}")
    print("")
    
    # Read all packets
    packets_16 = []  # Pairing mode packets
    packets_24 = []  # Normal mode packets
    
    with open(filename, 'r') as f:
        for line in f:
            parts = line.strip().split('\t')
            if len(parts) >= 2:
                data_hex = parts[-1].strip()
                if len(data_hex) == 32:  # 16 bytes
                    packets_16.append(data_hex)
                elif len(data_hex) == 48:  # 24 bytes
                    packets_24.append(data_hex)
    
    print(f"📊 Packet Summary:")
    print(f"   16-byte packets (pairing): {len(packets_16)}")
    print(f"   24-byte packets (normal): {len(packets_24)}")
    print("")
    
    # Analyze pairing packets (16 bytes)
    if packets_16:
        print("=" * 70)
        print("🎯 ANALYZING PAIRING MODE PACKETS (16 bytes)")
        print("=" * 70)
        print("Structure: [MAC:6][Address:1][Constant:1][MeshKey:4][Padding:4]")
        print("")
        
        # Take first unique packet
        unique_16 = list(set(packets_16))
        
        for i, pkt_hex in enumerate(unique_16[:3]):  # Show first 3
            data = bytes.fromhex(pkt_hex)
            print(f"Packet {i+1}: {pkt_hex}")
            print(f"  MAC address:  {data[0:6].hex()}")
            print(f"  Address:      {data[6]}")
            print(f"  Constant:     {data[7]}")
            print(f"  🔑 MESH KEY:  {data[8:12].hex()} (ASCII: '{data[8:12].decode('ascii', errors='replace')}')")
            print(f"  Padding:      {data[12:16].hex()}")
            print("")
        
        # Extract mesh key from first packet
        mesh_key = bytes.fromhex(unique_16[0])[8:12]
        print(f"✅ EXTRACTED MESH KEY: {mesh_key.hex()}")
        print(f"   ASCII representation: '{mesh_key.decode('ascii', errors='replace')}'")
        print("")
        
        return mesh_key
    
    # If no pairing packets, try to extract from normal packets
    if packets_24:
        print("=" * 70)
        print("🔬 ANALYZING NORMAL MODE PACKETS (24 bytes)")
        print("=" * 70)
        print("These are encrypted control commands")
        print("Structure: [Header:4][EncryptedPayload:20]")
        print("")
        
        # Show some examples
        unique_24 = list(set(packets_24))
        print(f"Found {len(unique_24)} unique 24-byte packets")
        print("")
        
        for i, pkt_hex in enumerate(unique_24[:5]):
            print(f"Packet {i+1}: {pkt_hex}")
            data = bytes.fromhex(pkt_hex)
            print(f"  Header (encrypted): {data[0:4].hex()}")
            print(f"  Payload (encrypted): {data[4:24].hex()}")
            print(f"  Last 4 bytes: {data[-4:].hex()}")
            print("")
        
        # Try XOR analysis
        if len(unique_24) >= 2:
            print("=" * 70)
            print("🔬 XOR ANALYSIS (Differential Cryptanalysis)")
            print("=" * 70)
            
            pkt1 = bytes.fromhex(unique_24[0])
            pkt2 = bytes.fromhex(unique_24[1])
            
            xor_result = bytes(a ^ b for a, b in zip(pkt1, pkt2))
            
            print(f"Packet 1: {pkt1.hex()}")
            print(f"Packet 2: {pkt2.hex()}")
            print(f"XOR:      {xor_result.hex()}")
            print("")
            print("Analysis:")
            print(f"  Header XOR:  {xor_result[0:4].hex()}")
            print(f"  Payload XOR: {xor_result[4:24].hex()}")
            print("")
            
            # Check if payloads look similar (mostly zeros after XOR = same payload)
            zeros = sum(1 for b in xor_result[4:24] if b == 0)
            print(f"  Zero bytes in payload XOR: {zeros}/20")
            if zeros > 15:
                print("  💡 Payloads are very similar - might be same command repeated")
            print("")
        
        # Try known-plaintext attack
        print("=" * 70)
        print("💡 KNOWN-PLAINTEXT ATTACK HINTS")
        print("=" * 70)
        print("Common payload patterns:")
        print("  Turn ON:  [01 XX RR GG BB ...] where XX=brightness, RGB=color")
        print("  Turn OFF: [00 XX RR GG BB ...]")
        print("")
        print("The last 4 bytes are often predictable padding or checksums")
        print("If we know the plaintext for last 4 bytes, we can XOR to get mesh key")
        print("")
        
        # Try common patterns
        print("🔍 Trying common payload endings...")
        test_packet = bytes.fromhex(unique_24[0])
        last_4 = test_packet[-4:]
        
        common_endings = {
            'All 0xFF': b'\xff\xff\xff\xff',
            'All 0x00': b'\x00\x00\x00\x00',
            'Mesh key itself (common)': b'',  # Will fill if we detect pattern
        }
        
        for name, pattern in common_endings.items():
            if not pattern:
                continue
            potential_key = bytes(a ^ b for a, b in zip(last_4, pattern))
            # Check if ASCII printable
            if all(32 <= b <= 126 for b in potential_key):
                print(f"  {name}: {potential_key.hex()} -> '{potential_key.decode('ascii')}'")
        
        print("")
        print("⚠️  Without a pairing packet, we need:")
        print("   1. Factory reset a light to get 16-byte pairing packet")
        print("   2. Use known plaintext (requires reverse engineering payloads)")
        print("   3. Capture many packets and do statistical analysis")
        print("")
        
        return None


if __name__ == "__main__":
    import os
    
    # Try to find the capture file
    search_paths = [
        'brmesh_ads.txt',
        '../brmesh_ads.txt',
        '../../brmesh_ads.txt',
    ]
    
    found_file = None
    for path in search_paths:
        if os.path.exists(path):
            found_file = path
            break
    
    if not found_file:
        print("❌ Could not find brmesh_ads.txt")
        print("   Please provide the path to your capture file")
        sys.exit(1)
    
    mesh_key = analyze_capture_file(found_file)
    
    if mesh_key:
        print("=" * 70)
        print("🎉 SUCCESS!")
        print("=" * 70)
        print(f"Mesh Key: {mesh_key.hex()}")
        print(f"ASCII:    '{mesh_key.decode('ascii', errors='replace')}'")
        print("")
        print("⚠️  SECURITY IMPLICATIONS:")
        print("   • This key grants FULL control over ALL devices in the network")
        print("   • Anyone within BLE range can capture this from pairing broadcasts")
        print("   • No additional authentication needed")
        print("   • The network has NO security boundary beyond BLE range")
        print("")
    else:
        print("=" * 70)
        print("❌ Could not extract mesh key from available packets")
        print("=" * 70)
        print("Next steps:")
        print("   1. Factory reset one light (5x on/off)")
        print("   2. Capture the 16-byte pairing advertisement")
        print("   3. Re-run this analysis")
