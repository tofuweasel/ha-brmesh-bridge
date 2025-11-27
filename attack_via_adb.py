"""
Attack BRMesh lights using ADB to send Bluetooth commands via phone
This bypasses Windows Bluetooth limitations by using your phone's BT adapter
"""
import subprocess
import time

MESH_KEY = bytes.fromhex('30323336')
TARGET = '78:B6:FE:60:E5:74'

# Writable characteristics we found
CHARACTERISTICS = [
    '00002b99-0000-1000-8000-00805f9b34fb',
    '00002b9a-0000-1000-8000-00805f9b34fb',
    '00002ba1-0000-1000-8000-00805f9b34fb',
    '00002ba4-0000-1000-8000-00805f9b34fb',
    '00002bbe-0000-1000-8000-00805f9b34fb',
    '594a3010-31db-11ea-978f-2e728ce88125'
]

def xor_encrypt(key, data):
    result = bytearray()
    for i, byte in enumerate(data):
        result.append(byte ^ key[i % len(key)])
    return bytes(result)

def generate_color_command(red, green, blue, white):
    header = bytes([0x06, 0x0c, 0x00, 0xff, 0xff, 0xff, 0xff])
    payload = bytes([red, green, blue, white, 0x00, 0x00, 0x00, 0x06])
    magic = bytes.fromhex('c47b365e')
    encrypted_header = xor_encrypt(magic, header)
    encrypted_payload = xor_encrypt(MESH_KEY, payload)
    return encrypted_header + encrypted_payload

def adb_shell(command):
    """Execute ADB shell command"""
    result = subprocess.run(
        ['adb', 'shell', command],
        capture_output=True,
        text=True,
        timeout=30
    )
    return result.stdout, result.stderr, result.returncode

def check_adb():
    """Check if ADB is available and phone is connected"""
    print("Checking ADB connection...")
    stdout, stderr, code = adb_shell('echo "ADB OK"')
    if code == 0 and "ADB OK" in stdout:
        print("✅ ADB connected!")
        return True
    else:
        print(f"❌ ADB not connected: {stderr}")
        return False

def check_gatttool():
    """Check if gatttool is available on phone"""
    print("\nChecking for gatttool on phone...")
    stdout, stderr, code = adb_shell('which gatttool')
    if code == 0 and 'gatttool' in stdout:
        print(f"✅ gatttool found: {stdout.strip()}")
        return True
    
    # Try bluetoothctl instead
    print("Checking for bluetoothctl...")
    stdout, stderr, code = adb_shell('which bluetoothctl')
    if code == 0 and 'bluetoothctl' in stdout:
        print(f"✅ bluetoothctl found: {stdout.strip()}")
        return 'bluetoothctl'
    
    print("❌ No Bluetooth tools found on phone")
    print("💡 We'll need to use a different approach...")
    return False

def attack_via_logcat():
    """
    Alternative: Use logcat to capture what YOUR PHONE sends,
    then we can reverse engineer the exact GATT characteristic and format
    """
    print("\n" + "="*70)
    print("📱 ALTERNATIVE APPROACH: CAPTURE YOUR PHONE'S BLE TRAFFIC")
    print("="*70)
    print("\nSince we can't send BLE commands directly via ADB,")
    print("let's capture what YOUR PHONE sends when you control the lights.")
    print("\nThis will show us:")
    print("  1. The exact GATT characteristic being used")
    print("  2. The exact command format")
    print("  3. Any differences from our protocol reverse engineering")
    print("\n🎮 Steps:")
    print("  1. I'll start capturing BLE traffic from your phone")
    print("  2. You control your light (turn it RED)")
    print("  3. We'll see exactly what was sent")
    print("  4. Then we can replicate it from your desktop!")
    print("\n" + "="*70)
    input("Press ENTER when ready to start capture...")
    
    print("\n📡 Starting BLE HCI snoop capture...")
    print("🎮 NOW: Open your phone app and turn the light RED!")
    print("   (Capturing for 15 seconds...)")
    
    # Just monitor logcat for BLE activity
    try:
        result = subprocess.run(
            ['adb', 'shell', 'timeout 15 logcat -b all *:V | grep -iE "ble|gatt|bluetooth"'],
            capture_output=True,
            text=True,
            timeout=20
        )
        print("\n📊 Capture complete!")
        
        if result.stdout:
            print("\n🔍 BLE Activity detected:")
            print("="*70)
            lines = result.stdout.split('\n')
            for line in lines[:50]:  # Show first 50 lines
                if line.strip():
                    print(line)
            if len(lines) > 50:
                print(f"\n... ({len(lines) - 50} more lines)")
        else:
            print("❌ No BLE activity captured")
            
    except Exception as e:
        print(f"❌ Capture failed: {e}")

def main():
    print("="*70)
    print("🔓 BRMESH ATTACK VIA ADB")
    print("="*70)
    print("\nAttempting to control BRMesh lights using your phone's Bluetooth")
    print("instead of your desktop's Bluetooth adapter.")
    print("="*70)
    
    if not check_adb():
        print("\n❌ Please connect your phone via USB and enable ADB debugging")
        return
    
    tool = check_gatttool()
    
    if not tool:
        # Fallback to capturing what the phone sends
        attack_via_logcat()
        return
    
    print("\n" + "="*70)
    print("🎯 SENDING ATTACK COMMANDS VIA PHONE")
    print("="*70)
    
    # Generate commands
    colors = [
        ("RED", 255, 0, 0, 0),
        ("BLUE", 0, 0, 255, 0),
        ("WHITE", 0, 0, 0, 255)
    ]
    
    for name, r, g, b, w in colors:
        cmd = generate_color_command(r, g, b, w)
        hex_cmd = cmd.hex()
        
        print(f"\n🎨 Sending {name} command...")
        print(f"   Command: {hex_cmd}")
        
        # Try each characteristic
        for char_uuid in CHARACTERISTICS:
            if tool == 'bluetoothctl':
                # Use bluetoothctl
                adb_cmd = f'bluetoothctl -- gatt.write-value {TARGET} {char_uuid} {hex_cmd}'
            else:
                # Use gatttool
                adb_cmd = f'gatttool -b {TARGET} -t random --char-write-req --handle={char_uuid} --value={hex_cmd}'
            
            stdout, stderr, code = adb_shell(adb_cmd)
            if code == 0:
                print(f"   ✅ Sent via {char_uuid}")
                break
            else:
                print(f"   ❌ Failed on {char_uuid}: {stderr}")
        
        time.sleep(2)
    
    print("\n" + "="*70)
    print("✅ ATTACK COMPLETE - Did your light change colors?")
    print("="*70)

if __name__ == "__main__":
    main()
