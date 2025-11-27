#!/usr/bin/env python3
"""
BRMesh Control Protocol Implementation
Reverse engineered from libbroadlink_ble.so

Functions:
- package_ble_fastcon_body: Main control command encryption (24 bytes)
- package_ble_fastcon_body_with_header: Header + encryption
- package_ble_fastcon_body_without_encrty: Unencrypted control command
"""

def package_ble_fastcon_body_without_encrty(
    cmd_type: int,      # param_1: Command type (0-7, 3 bits)
    retry: int,         # param_2: Retry counter (0-15, 4 bits)
    seq: int,           # param_3: Sequence number
    mesh_byte: int,     # param_4: Mesh byte
    forward: int,       # param_5: Forward flag (0 or 1)
    payload: bytes,     # param_6: Payload data
) -> bytes:
    """
    Creates unencrypted control command structure.
    Returns command without encryption (param_7 + 4 bytes).
    """
    # Build header byte 0: retry (low 4 bits) | cmd_type (bits 4-6) | forward (bit 7)
    byte0 = (retry & 0x0F) | ((cmd_type & 0x07) << 4) | ((forward & 0x01) << 7)
    
    # Build 4-byte header
    header = bytes([
        byte0,
        seq & 0xFF,
        mesh_byte & 0xFF,
        0  # byte 3 will be filled with checksum
    ])
    
    # Create output buffer
    output = bytearray(4 + len(payload))
    output[0:4] = header
    output[4:] = payload
    
    # Calculate checksum (sum of all bytes except byte 3, stored in byte 3)
    checksum = 0
    for i in range(len(output)):
        if i != 3:  # Skip byte 3 itself
            checksum += output[i]
    
    output[3] = checksum & 0xFF
    
    return bytes(output)


def package_ble_fastcon_body(
    cmd_type: int,      # param_1: Command type (0-7, 3 bits)
    retry: int,         # param_2: Retry counter (0-15, 4 bits)
    seq: int,           # param_3: Sequence number
    mesh_byte: int,     # param_4: Mesh byte
    forward: int,       # param_5: Forward flag (0 or 1)
    payload: bytes,     # param_6: Payload data
    mesh_key: bytes = None,  # param_9: 4-byte mesh key (or None for default)
) -> bytes:
    """
    Creates encrypted control command.
    
    Process:
    1. Build 4-byte header
    2. Calculate checksum XOR with magic constant
    3. XOR payload with mesh key (repeating 4-byte pattern)
    4. Return encrypted command
    
    Returns 24 bytes for typical control commands.
    """
    # Build header byte 0
    byte0 = (retry & 0x0F) | ((cmd_type & 0x07) << 4) | ((forward & 0x01) << 7)
    
    # Build initial header
    header = bytearray([
        byte0,
        seq & 0xFF,
        mesh_byte & 0xFF,
        0  # Placeholder for checksum
    ])
    
    # Copy header and payload to output
    output = bytearray(4 + len(payload))
    output[0:4] = header
    output[4:] = payload
    
    # Calculate checksum (sum of all bytes except byte 3)
    checksum = 0
    for i in range(len(output)):
        if i != 3:  # Skip byte 3 position
            checksum += output[i]
    
    # XOR checksum with magic constant 0xc47b365e
    # This modifies the 4-byte header
    magic = 0xc47b365e
    header_with_checksum = int.from_bytes(header, byteorder='little')
    header_with_checksum = (header_with_checksum & 0xFFFFFF00) | (checksum & 0xFF)
    header_with_checksum ^= magic
    
    # Write back modified header
    output[0:4] = header_with_checksum.to_bytes(4, byteorder='little')
    
    # XOR payload with mesh key (if provided)
    if mesh_key and len(mesh_key) >= 4:
        payload_start = 4
        payload_len = len(payload)
        
        for i in range(payload_len):
            # XOR each payload byte with corresponding mesh key byte (cycling every 4 bytes)
            output[payload_start + i] ^= mesh_key[i & 3]
    
    # Copy encrypted payload back
    output[4:] = output[4:4+len(payload)]
    
    return bytes(output)


def package_ble_fastcon_body_with_header(
    header: bytes,      # param_1: 4-byte header (already built)
    payload: bytes,     # param_2: Payload to encrypt
    mesh_key: bytes = None,  # param_5: 4-byte mesh key
) -> bytes:
    """
    Encrypts header and payload.
    
    Process:
    1. XOR header with magic constant 0x5e367bc4 (byte by byte reversed)
    2. XOR payload with mesh key (repeating 4-byte pattern)
    3. Return encrypted command
    """
    # Copy header and XOR with magic constant
    output = bytearray(4 + len(payload))
    magic_bytes = [0x5e, 0x36, 0x7b, 0xc4]
    
    for i in range(4):
        output[i] = header[i] ^ magic_bytes[i]
    
    # Copy payload
    encrypted_payload = bytearray(payload)
    
    # XOR payload with mesh key if provided
    if mesh_key and len(mesh_key) >= 4:
        for i in range(len(encrypted_payload)):
            encrypted_payload[i] ^= mesh_key[i & 3]
    
    # Copy encrypted payload to output
    output[4:] = encrypted_payload
    
    return bytes(output)


def create_control_command(
    address: int,
    cmd_type: int,
    payload: bytes,
    mesh_key: bytes,
    seq: int = 0,
    retry: int = 0,
    forward: int = 0,
    mesh_byte: int = 0,
) -> bytes:
    """
    High-level API to create encrypted control command.
    
    Args:
        address: Target device address (1-255)
        cmd_type: Command type (0-7)
            - 0: Status query
            - 1: Control (on/off/brightness/color)
            - 2: Pairing
            - 3: Group command
            - 4: Scene
            - 5-7: Reserved
        payload: Command payload (typically 20 bytes for 24-byte total)
        mesh_key: 4-byte mesh key
        seq: Sequence number (0-255)
        retry: Retry counter (0-15)
        forward: Forward flag (0 or 1)
        mesh_byte: Mesh byte (0-255)
    
    Returns:
        Encrypted command bytes (typically 24 bytes)
    """
    return package_ble_fastcon_body(
        cmd_type=cmd_type,
        retry=retry,
        seq=seq,
        mesh_byte=mesh_byte,
        forward=forward,
        payload=payload,
        mesh_key=mesh_key,
    )


def decode_control_command(
    encrypted: bytes,
    mesh_key: bytes,
) -> dict:
    """
    Decode encrypted control command.
    
    Args:
        encrypted: Encrypted command bytes
        mesh_key: 4-byte mesh key
    
    Returns:
        Dictionary with decoded fields
    """
    if len(encrypted) < 4:
        raise ValueError("Command too short (need at least 4 bytes)")
    
    # Decrypt header by XORing with magic constant
    magic = 0xc47b365e
    header_encrypted = int.from_bytes(encrypted[0:4], byteorder='little')
    header_decrypted = header_encrypted ^ magic
    header_bytes = header_decrypted.to_bytes(4, byteorder='little')
    
    # Parse header
    byte0 = header_bytes[0]
    retry = byte0 & 0x0F
    cmd_type = (byte0 >> 4) & 0x07
    forward = (byte0 >> 7) & 0x01
    seq = header_bytes[1]
    mesh_byte = header_bytes[2]
    checksum = header_bytes[3]
    
    # Decrypt payload
    payload_encrypted = encrypted[4:]
    payload_decrypted = bytearray(payload_encrypted)
    
    if mesh_key and len(mesh_key) >= 4:
        for i in range(len(payload_decrypted)):
            payload_decrypted[i] ^= mesh_key[i & 3]
    
    return {
        'cmd_type': cmd_type,
        'retry': retry,
        'seq': seq,
        'mesh_byte': mesh_byte,
        'forward': forward,
        'checksum': checksum,
        'payload': bytes(payload_decrypted),
    }


# Test cases
if __name__ == "__main__":
    print("BRMesh Control Protocol Test")
    print("=" * 60)
    
    # Test 1: Unencrypted command
    print("\nTest 1: Unencrypted command")
    payload = bytes([0x01, 0x64, 0xFF, 0xFF, 0xFF])  # Example: Turn on, brightness 100, white
    unencrypted = package_ble_fastcon_body_without_encrty(
        cmd_type=1,      # Control command
        retry=0,
        seq=1,
        mesh_byte=0,
        forward=0,
        payload=payload
    )
    print(f"  Payload: {payload.hex()}")
    print(f"  Command ({len(unencrypted)} bytes): {unencrypted.hex()}")
    
    # Test 2: Encrypted command with mesh key
    print("\nTest 2: Encrypted command")
    mesh_key = bytes.fromhex("30323336")  # "0236" in ASCII
    encrypted = package_ble_fastcon_body(
        cmd_type=1,
        retry=0,
        seq=1,
        mesh_byte=0,
        forward=0,
        payload=payload,
        mesh_key=mesh_key
    )
    print(f"  Mesh Key: {mesh_key.hex()}")
    print(f"  Payload: {payload.hex()}")
    print(f"  Encrypted ({len(encrypted)} bytes): {encrypted.hex()}")
    
    # Test 3: Decode encrypted command
    print("\nTest 3: Decode encrypted command")
    decoded = decode_control_command(encrypted, mesh_key)
    print(f"  Command Type: {decoded['cmd_type']}")
    print(f"  Sequence: {decoded['seq']}")
    print(f"  Retry: {decoded['retry']}")
    print(f"  Forward: {decoded['forward']}")
    print(f"  Checksum: 0x{decoded['checksum']:02x}")
    print(f"  Payload: {decoded['payload'].hex()}")
    print(f"  Matches original: {decoded['payload'] == payload}")
    
    # Test 4: Header encryption variant
    print("\nTest 4: Header encryption variant")
    header = bytes([0x10, 0x01, 0x00, 0x00])  # Pre-built header
    encrypted_variant = package_ble_fastcon_body_with_header(
        header=header,
        payload=payload,
        mesh_key=mesh_key
    )
    print(f"  Header: {header.hex()}")
    print(f"  Encrypted ({len(encrypted_variant)} bytes): {encrypted_variant.hex()}")
    
    print("\n" + "=" * 60)
    print("SUCCESS! Control protocol implemented.")
    print("\nNOTE: The 'magic constant' 0xc47b365e appears to be:")
    print("  - XORed with header checksum in package_ble_fastcon_body")
    print("  - Related to 0x5e367bc4 (byte-reversed) in package_ble_fastcon_body_with_header")
    print("\nNext steps:")
    print("1. Test with actual captured control commands")
    print("2. Verify on/off/brightness/color commands")
    print("3. Integrate into ESP BLE Bridge addon")
