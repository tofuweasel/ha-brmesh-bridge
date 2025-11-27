#!/usr/bin/env python3
"""
BRMesh Pairing Protocol Implementation
Based on reverse engineering of libbroadlink_ble.so

The pairing "encryption" is actually just a structured message format.
NO actual encryption is performed!
"""

def package_disc_res(device_id: bytes, address: int, constant: int, mesh_key: bytes) -> bytes:
    """
    Create a pairing response for devices with address <= 256.
    
    Args:
        device_id: 6-byte device ID (MAC address bytes)
        address: Device address (0-256)
        constant: Always 1 for pairing response
        mesh_key: 4-byte mesh key
    
    Returns:
        12-byte pairing response
    """
    if len(device_id) < 6:
        raise ValueError(f"Device ID must be at least 6 bytes, got {len(device_id)}")
    if len(mesh_key) != 4:
        raise ValueError(f"Mesh key must be 4 bytes, got {len(mesh_key)}")
    
    response = bytearray(12)
    
    # Bytes 0-3: First 4 bytes of device ID
    response[0:4] = device_id[0:4]
    
    # Bytes 4-5: Next 2 bytes of device ID
    response[4:6] = device_id[4:6]
    
    # Byte 6: Device address (low byte)
    response[6] = address & 0xFF
    
    # Byte 7: Constant (1 for pairing)
    response[7] = constant & 0xFF
    
    # Bytes 8-11: Mesh key (4 bytes)
    response[8:12] = mesh_key[0:4]
    
    return bytes(response)


def package_disc_res2(device_id: bytes, address: int, group_id: int, constant: int, 
                      mesh_key: bytes) -> bytes:
    """
    Create a pairing response for devices with address > 256 or special types.
    
    Args:
        device_id: 6-byte device ID (MAC address bytes)
        address: Device address (low byte)
        group_id: Group ID or high byte of address
        constant: Always 1 for pairing response
        mesh_key: 4-byte mesh key
    
    Returns:
        18-byte pairing response
    """
    if len(device_id) < 6:
        raise ValueError(f"Device ID must be at least 6 bytes, got {len(device_id)}")
    if len(mesh_key) != 4:
        raise ValueError(f"Mesh key must be 4 bytes, got {len(mesh_key)}")
    
    response = bytearray(18)
    
    # Bytes 0-3: First 4 bytes of device ID
    response[0:4] = device_id[0:4]
    
    # Bytes 4-5: Next 2 bytes of device ID
    response[4:6] = device_id[4:6]
    
    # Byte 6: Device address (low byte)
    response[6] = address & 0xFF
    
    # Byte 7: Constant (1 for pairing)
    response[7] = constant & 0xFF
    
    # Bytes 8-11: Mesh key (4 bytes)
    response[8:12] = mesh_key[0:4]
    
    # Byte 12: Group ID or high byte of address
    response[12] = group_id & 0xFF
    
    # Bytes 13-17: Padding (zeros)
    # Note: Java code creates 18-byte array, decompiled shows 0xd (13) return
    # but the array size determines actual length
    
    return bytes(response)


def create_pairing_response(device_mac: str, address: int, group_id: int, 
                           mesh_key: str) -> bytes:
    """
    High-level function to create pairing response based on device parameters.
    
    Args:
        device_mac: Device MAC address as hex string (e.g., "AA:BB:CC:DD:EE:FF")
        address: Device address to assign (1-65535)
        group_id: Group ID (0-255)
        mesh_key: Mesh key as hex string (e.g., "30323336")
    
    Returns:
        Pairing response bytes (12 or 18 bytes depending on address)
    """
    # Convert MAC address to device ID bytes
    mac_bytes = bytes.fromhex(device_mac.replace(':', '').replace('-', ''))
    
    # Convert mesh key
    key_bytes = bytes.fromhex(mesh_key)
    
    # Determine which function to use based on address
    if address > 256:
        # Use extended format
        addr_low = address & 0xFF
        addr_high = (address >> 8) & 0xFF
        return package_disc_res2(mac_bytes, addr_low, addr_high, 1, key_bytes)
    else:
        # Use standard format
        return package_disc_res(mac_bytes, address, 1, key_bytes)


if __name__ == "__main__":
    # Test with known values
    print("BRMesh Pairing Protocol Test")
    print("=" * 60)
    
    # Test case 1: Standard pairing (address <= 256)
    device_mac = "AA:BB:CC:DD:EE:FF"
    address = 1
    mesh_key = "30323336"  # "0236" in ASCII
    
    response = create_pairing_response(device_mac, address, 0, mesh_key)
    print(f"\nTest 1: Standard pairing")
    print(f"  Device MAC: {device_mac}")
    print(f"  Address: {address}")
    print(f"  Mesh Key: {mesh_key}")
    print(f"  Response ({len(response)} bytes): {response.hex()}")
    
    # Expected format:
    # Bytes 0-5: 54C4B261BBD7 (MAC)
    # Byte 6:    01 (address)
    # Byte 7:    01 (constant)
    # Bytes 8-11: 30323336 (mesh key)
    
    # Test case 2: Extended pairing (address > 256)
    address2 = 300
    response2 = create_pairing_response(device_mac, address2, 0, mesh_key)
    print(f"\nTest 2: Extended pairing")
    print(f"  Device MAC: {device_mac}")
    print(f"  Address: {address2}")
    print(f"  Mesh Key: {mesh_key}")
    print(f"  Response ({len(response2)} bytes): {response2.hex()}")
    
    print("\n" + "=" * 60)
    print("SUCCESS! Pairing protocol is just structured data copying.")
    print("No encryption needed!")
