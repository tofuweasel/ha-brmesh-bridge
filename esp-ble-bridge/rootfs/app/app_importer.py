#!/usr/bin/env python3
"""
BRMesh App Configuration Importer
Parse exported config from BRMesh Android app
"""
import json
import logging
import re
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)

class BRMeshAppImporter:
    """
    Import configuration from BRMesh Android app
    
    The BRMesh app stores configuration in SharedPreferences or database
    Can be extracted via:
    1. ADB backup
    2. Root access to /data/data/com.broadlink.brmesh/
    3. App export feature (if available)
    """
    
    def __init__(self, bridge):
        self.bridge = bridge
    
    def import_from_adb_logcat(self, logcat_output: str) -> Dict:
        """
        Parse device configuration from ADB logcat output
        
        Usage:
        adb logcat -d > logcat.txt
        importer.import_from_adb_logcat(open('logcat.txt').read())
        """
        config = {
            'mesh_key': None,
            'devices': []
        }
        
        # Extract mesh key
        mesh_key_pattern = r'jyq_helper.*key:\s*(\w{8})'
        mesh_match = re.search(mesh_key_pattern, logcat_output)
        if mesh_match:
            config['mesh_key'] = mesh_match.group(1)
            logger.info(f"Found mesh key: {config['mesh_key']}")
        
        # Extract device payloads
        payload_pattern = r'payload:\s*([0-9a-f]+)'
        for match in re.finditer(payload_pattern, logcat_output, re.IGNORECASE):
            payload_hex = match.group(1)
            device = self._parse_payload(payload_hex)
            if device:
                # Avoid duplicates
                if not any(d['device_id'] == device['device_id'] for d in config['devices']):
                    config['devices'].append(device)
                    logger.info(f"Parsed device {device['device_id']} from payload")
        
        return config
    
    def _parse_payload(self, payload_hex: str) -> Optional[Dict]:
        """
        Parse BRMesh BLE payload
        
        Format: [CMD, DEVICE_ID, R, G, B, W, BRIGHTNESS, POWER, ...]
        """
        try:
            payload_bytes = bytes.fromhex(payload_hex)
            if len(payload_bytes) < 8:
                return None
            
            cmd = payload_bytes[0]
            device_id = payload_bytes[1]
            r = payload_bytes[2]
            g = payload_bytes[3]
            b = payload_bytes[4]
            w = payload_bytes[5]
            brightness = payload_bytes[6]
            power = payload_bytes[7]
            
            return {
                'device_id': device_id,
                'state': {
                    'state': power == 1,
                    'brightness': brightness,
                    'rgb': [r, g, b],
                    'white': w
                }
            }
        except Exception as e:
            logger.debug(f"Failed to parse payload {payload_hex}: {e}")
            return None
    
    def import_from_json_export(self, json_path: str) -> Dict:
        """
        Import from JSON export file
        
        Expected format:
        {
            "mesh_key": "30323336",
            "devices": [
                {
                    "id": 10,
                    "name": "Living Room Light",
                    "type": "RGBW"
                }
            ]
        }
        """
        try:
            with open(json_path, 'r') as f:
                data = json.load(f)
            
            logger.info(f"Loaded config from {json_path}")
            return data
        except Exception as e:
            logger.error(f"Failed to load JSON export: {e}")
            return {}
    
    def import_from_shared_prefs(self, prefs_xml: str) -> Dict:
        """
        Import from Android SharedPreferences XML
        
        Extract via:
        adb pull /data/data/com.broadlink.brmesh/shared_prefs/
        """
        config = {
            'mesh_key': None,
            'devices': []
        }
        
        # Parse XML for mesh key
        mesh_key_pattern = r'<string name="mesh_key">(\w+)</string>'
        mesh_match = re.search(mesh_key_pattern, prefs_xml)
        if mesh_match:
            config['mesh_key'] = mesh_match.group(1)
        
        # Parse device list (format varies by app version)
        device_pattern = r'<string name="device_(\d+)">([^<]+)</string>'
        for match in re.finditer(device_pattern, prefs_xml):
            device_id = int(match.group(1))
            device_data = match.group(2)
            
            # Parse device data (usually JSON string)
            try:
                device_json = json.loads(device_data)
                config['devices'].append({
                    'device_id': device_id,
                    'name': device_json.get('name', f'Light {device_id}'),
                    'type': device_json.get('type', 'RGBW')
                })
            except:
                # Fallback if not JSON
                config['devices'].append({
                    'device_id': device_id,
                    'name': f'Light {device_id}'
                })
        
        return config
    
    def sync_device_names_from_app(self) -> int:
        """
        Attempt to sync device names from BRMesh app via ADB
        
        Returns number of devices updated
        """
        logger.info("Attempting to sync device names from BRMesh app...")
        
        try:
            import subprocess
            
            # Get ADB logcat with device info
            result = subprocess.run(
                ['adb', 'logcat', '-d'],
                capture_output=True,
                text=True,
                timeout=10
            )
            
            if result.returncode != 0:
                logger.error("ADB not available or device not connected")
                return 0
            
            # Parse logcat
            config = self.import_from_adb_logcat(result.stdout)
            
            # Update mesh key if found
            if config['mesh_key']:
                self.bridge.mesh_key = config['mesh_key']
                logger.info(f"Updated mesh key: {config['mesh_key']}")
            
            # Update device states (but not overwrite custom names)
            updated = 0
            for device in config['devices']:
                device_id = device['device_id']
                if device_id in self.bridge.lights:
                    # Update state only
                    if 'state' in device:
                        self.bridge.lights[device_id]['state'].update(device['state'])
                        updated += 1
            
            logger.info(f"Updated {updated} device states from app")
            return updated
            
        except Exception as e:
            logger.error(f"Failed to sync from app: {e}")
            return 0
    
    def apply_imported_config(self, imported_config: Dict) -> bool:
        """
        Apply imported configuration to bridge
        
        Merges imported devices with existing configuration
        """
        try:
            # Update mesh key
            if imported_config.get('mesh_key'):
                self.bridge.config['mesh_key'] = imported_config['mesh_key']
                self.bridge.mesh_key = imported_config['mesh_key']
            
            # Add/update devices
            for device in imported_config.get('devices', []):
                device_id = device['device_id']
                
                if device_id not in self.bridge.lights:
                    # New device - add it
                    self.bridge.lights[device_id] = {
                        'name': device.get('name', f'BRMesh Light {device_id}'),
                        'device_type': device.get('device_type', 'bulb'),
                        'state': device.get('state', {
                            'state': False,
                            'brightness': 255,
                            'rgb': [255, 255, 255]
                        }),
                        'color_interlock': True,
                        'location': {'x': None, 'y': None},
                        'signal_strength': {}
                    }
                    logger.info(f"Added device {device_id} from import")
                else:
                    # Existing device - update name if not customized
                    if device.get('name'):
                        current_name = self.bridge.lights[device_id]['name']
                        # Only update if current name is auto-generated
                        if current_name.startswith('BRMesh Light'):
                            self.bridge.lights[device_id]['name'] = device['name']
                            logger.info(f"Updated device {device_id} name to '{device['name']}'")
            
            # Save configuration
            self.bridge.save_config()
            
            # Republish MQTT discovery
            if self.bridge.mqtt_client:
                self.bridge.publish_discovery()
            
            logger.info(f"Applied configuration with {len(imported_config.get('devices', []))} devices")
            return True
            
        except Exception as e:
            logger.error(f"Failed to apply imported config: {e}")
            return False
