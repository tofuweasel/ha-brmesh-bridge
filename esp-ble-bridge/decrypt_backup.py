#!/usr/bin/env python3
"""
Decrypt BRMesh backup file using the mesh encryption key
"""
import base64
import json
from Crypto.Cipher import AES
from Crypto.Util.Padding import unpad

def decrypt_backup(encrypted_file, output_file):
    # Read and decode base64
    with open(encrypted_file, 'rb') as f:
        encrypted_data = base64.b64decode(f.read())
    
    print(f"Encrypted data length: {len(encrypted_data)} bytes")
    print(f"First 32 bytes (hex): {encrypted_data[:32].hex()}")
    
    # From pairing capture: mesh key = "30323336" (ASCII "0236")
    # Encryption key = 5e367bc4 (derived from mesh key)
    mesh_key = bytes.fromhex('30323336')  # "0236" in hex
    encryption_key = bytes.fromhex('5e367bc4')  # From logcat
    
    # Try different decryption approaches
    attempts = [
        ("Direct mesh key (16 bytes padded)", mesh_key.ljust(16, b'\x00')),
        ("Direct mesh key (32 bytes padded)", mesh_key.ljust(32, b'\x00')),
        ("Encryption key (16 bytes padded)", encryption_key.ljust(16, b'\x00')),
        ("Encryption key (32 bytes padded)", encryption_key.ljust(32, b'\x00')),
        ("Mesh key repeated", (mesh_key * 4)[:16]),
        ("Encryption key repeated", (encryption_key * 4)[:16]),
    ]
    
    for name, key in attempts:
        print(f"\nTrying: {name}")
        print(f"Key (hex): {key.hex()}")
        
        try:
            # Try ECB mode first (simpler)
            cipher = AES.new(key, AES.MODE_ECB)
            decrypted = cipher.decrypt(encrypted_data)
            
            # Try to remove padding
            try:
                unpadded = unpad(decrypted, AES.block_size)
                # Try to parse as JSON
                data = json.loads(unpadded.decode('utf-8'))
                print(f"✓ SUCCESS with {name}!")
                
                # Save decrypted data
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                
                print(f"\nDecrypted config saved to: {output_file}")
                print(f"Keys in config: {list(data.keys())}")
                if 'deviceList' in data:
                    print(f"Devices: {len(data['deviceList'])}")
                if 'groupList' in data:
                    print(f"Groups: {len(data['groupList'])}")
                if 'sceneList' in data:
                    print(f"Scenes: {len(data['sceneList'])}")
                return True
                
            except Exception as e:
                print(f"  Unpadding/JSON parse failed: {e}")
                # Try without unpadding
                try:
                    data = json.loads(decrypted.decode('utf-8').rstrip('\x00'))
                    print(f"✓ SUCCESS (no padding) with {name}!")
                    with open(output_file, 'w') as f:
                        json.dump(data, f, indent=2)
                    return True
                except:
                    pass
                    
        except Exception as e:
            print(f"  ECB mode failed: {e}")
        
        # Try CBC mode with IV from start of data
        try:
            iv = encrypted_data[:16]
            ciphertext = encrypted_data[16:]
            cipher = AES.new(key, AES.MODE_CBC, iv)
            decrypted = cipher.decrypt(ciphertext)
            
            try:
                unpadded = unpad(decrypted, AES.block_size)
                data = json.loads(unpadded.decode('utf-8'))
                print(f"✓ SUCCESS (CBC) with {name}!")
                
                with open(output_file, 'w') as f:
                    json.dump(data, f, indent=2)
                return True
            except:
                pass
        except Exception as e:
            print(f"  CBC mode failed: {e}")
    
    print("\n✗ All decryption attempts failed")
    print("\nThe backup may use a different encryption scheme.")
    print("The QR codes are for phone-to-phone sharing and may use device-specific keys.")
    return False

if __name__ == '__main__':
    success = decrypt_backup(
        'BRMESH_BACKUP20251126145314.json',
        'app_config_decrypted.json'
    )
    
    if not success:
        print("\nAlternative: Use ADB to extract the SQLite database directly")
        print("  adb backup -f backup.ab com.brgd.brblmesh")
        print("  Then extract the .ab file to get databases")
