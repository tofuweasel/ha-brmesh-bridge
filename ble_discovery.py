#!/usr/bin/env python3
"""
BLE Discovery and Device Registration for BRMesh Lights
Allows ESP32 to discover and register new devices without phone
"""
import asyncio
import logging
import struct
from typing import Dict, List, Optional
from bleak import BleakScanner, BleakClient
import json

logger = logging.getLogger(__name__)

class BRMeshDiscovery:
    """
    BRMesh device discovery and registration
    
    BRMesh lights broadcast BLE advertisements with manufacturer data
    We can scan for these and extract device IDs
    """
    
    def __init__(self, bridge):
        self.bridge = bridge
        self.discovered_devices = {}
        self.scanning = False
        
        # BRMesh manufacturer ID (if known) or characteristic UUIDs
        self.brmesh_identifiers = [
            "0000fff3",  # Common BRMesh service UUID
            "0000fff4",  # BRMesh characteristic
        ]
    
    async def scan_for_devices(self, duration: int = 30) -> List[Dict]:
        """
        Scan for BRMesh devices via BLE
        
        Returns list of discovered devices with:
        - device_id: Extracted light ID
        - mac_address: BLE MAC
        - rssi: Signal strength
        - name: Device name if available
        """
        logger.info(f"Starting BLE scan for {duration} seconds...")
        self.scanning = True
        discovered = []
        
        def detection_callback(device, advertisement_data):
            """Called for each discovered device"""
            # Check if this looks like a BRMesh device
            if self._is_brmesh_device(device, advertisement_data):
                device_info = self._extract_device_info(device, advertisement_data)
                if device_info and device_info['device_id'] not in [d['device_id'] for d in discovered]:
                    discovered.append(device_info)
                    logger.info(f"Discovered BRMesh device: ID={device_info['device_id']}, "
                              f"MAC={device_info['mac_address']}, RSSI={device_info['rssi']}")
        
        try:
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(duration)
            await scanner.stop()
        except Exception as e:
            logger.error(f"BLE scan error: {e}")
        finally:
            self.scanning = False
        
        logger.info(f"Scan complete. Found {len(discovered)} BRMesh devices")
        return discovered
    
    def _is_brmesh_device(self, device, advertisement_data) -> bool:
        """Check if device is a BRMesh light"""
        # Method 1: Check manufacturer data
        if advertisement_data.manufacturer_data:
            # BRMesh devices typically have specific manufacturer IDs
            # This needs to be determined by analyzing actual devices
            for mfr_id, data in advertisement_data.manufacturer_data.items():
                # Common BLE manufacturer IDs for Chinese smart devices
                if mfr_id in [0x0000, 0xFFFF]:  # Generic/Unknown
                    return True
        
        # Method 2: Check service UUIDs
        if advertisement_data.service_uuids:
            for uuid in advertisement_data.service_uuids:
                if any(ident in uuid.lower() for ident in self.brmesh_identifiers):
                    return True
        
        # Method 3: Check device name patterns
        name = device.name or ""
        if any(pattern in name.lower() for pattern in ['brmesh', 'fastcon', 'melpo', 'mesh_']):
            return True
        
        return False
    
    def _extract_device_info(self, device, advertisement_data) -> Optional[Dict]:
        """Extract device ID and info from BLE advertisement"""
        info = {
            'device_id': None,
            'mac_address': device.address,
            'rssi': advertisement_data.rssi,
            'name': device.name or f"BRMesh Light {device.address[-5:]}"
        }
        
        # Try to extract device ID from manufacturer data
        if advertisement_data.manufacturer_data:
            for mfr_id, data in advertisement_data.manufacturer_data.items():
                # BRMesh encodes device ID in manufacturer data
                # Format varies, but often first few bytes contain ID
                if len(data) >= 2:
                    # Try interpreting as device ID
                    potential_id = data[0] if len(data) > 0 else None
                    if potential_id and 1 <= potential_id <= 255:
                        info['device_id'] = potential_id
                        return info
        
        # If we can't extract ID, we'll need pairing mode
        return info
    
    async def enter_pairing_mode(self, device_mac: str, timeout: int = 60) -> Optional[int]:
        """
        Enter pairing mode for a new device
        
        This attempts to connect to the device and trigger pairing
        Returns the assigned device ID if successful
        """
        logger.info(f"Entering pairing mode for device {device_mac}")
        
        try:
            async with BleakClient(device_mac, timeout=timeout) as client:
                if not client.is_connected:
                    logger.error(f"Failed to connect to {device_mac}")
                    return None
                
                # Read device characteristics to find ID
                services = await client.get_services()
                
                for service in services:
                    for char in service.characteristics:
                        if 'read' in char.properties:
                            try:
                                value = await client.read_gatt_char(char.uuid)
                                logger.debug(f"Characteristic {char.uuid}: {value.hex()}")
                                
                                # Look for device ID in characteristics
                                # This is device-specific and may need adjustment
                                if len(value) >= 1:
                                    potential_id = value[0]
                                    if 1 <= potential_id <= 255:
                                        logger.info(f"Found device ID: {potential_id}")
                                        return potential_id
                            except Exception as e:
                                logger.debug(f"Could not read {char.uuid}: {e}")
                
        except Exception as e:
            logger.error(f"Pairing mode error: {e}")
        
        return None
    
    async def register_device(self, device_id: int, name: Optional[str] = None) -> bool:
        """
        Register a discovered device in the bridge configuration
        
        This adds the device to lights array and saves config
        """
        if device_id in self.bridge.lights:
            logger.warning(f"Device {device_id} already registered")
            return False
        
        # Generate name if not provided
        if not name:
            name = f"BRMesh Light {device_id}"
        
        # Add to lights
        self.bridge.lights[device_id] = {
            'name': name,
            'state': {'state': False, 'brightness': 255, 'rgb': [255, 255, 255]},
            'location': {'x': None, 'y': None},
            'color_interlock': True,
            'signal_strength': {}
        }
        
        # Update config file
        try:
            with open('/data/options.json', 'r') as f:
                config = json.load(f)
            
            if 'lights' not in config:
                config['lights'] = []
            
            config['lights'].append({
                'light_id': device_id,
                'name': name,
                'color_interlock': True,
                'supports_cwww': False,
                'location': {'x': None, 'y': None}
            })
            
            with open('/data/options.json', 'w') as f:
                json.dump(config, f, indent=2)
            
            logger.info(f"Registered device {device_id} as '{name}'")
            
            # Publish MQTT discovery
            if self.bridge.mqtt_client:
                self.bridge.publish_discovery()
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to register device: {e}")
            return False
    
    async def auto_discover_and_register(self, duration: int = 30) -> List[int]:
        """
        Automatic discovery and registration workflow
        
        1. Scan for devices
        2. Filter out already registered
        3. Register new ones
        """
        discovered = await self.scan_for_devices(duration)
        registered_ids = []
        
        for device in discovered:
            device_id = device.get('device_id')
            
            if not device_id:
                # Try pairing mode
                logger.info(f"Attempting to pair with {device['mac_address']}")
                device_id = await self.enter_pairing_mode(device['mac_address'])
            
            if device_id and device_id not in self.bridge.lights:
                success = await self.register_device(device_id, device['name'])
                if success:
                    registered_ids.append(device_id)
        
        return registered_ids
    
    async def query_light_state(self, device_id: int) -> Optional[Dict]:
        """
        Query a light for its current state
        
        BRMesh lights broadcast their state in BLE advertisements
        We scan for the specific device and decode its state
        """
        logger.info(f"Querying state for light {device_id}")
        
        # Scan for the specific device
        state = None
        
        def detection_callback(device, advertisement_data):
            nonlocal state
            if self._is_brmesh_device(device, advertisement_data):
                info = self._extract_device_info(device, advertisement_data)
                if info and info.get('device_id') == device_id:
                    # Try to decode state from advertisement
                    state = self._decode_state_from_advertisement(advertisement_data)
        
        try:
            scanner = BleakScanner(detection_callback=detection_callback)
            await scanner.start()
            await asyncio.sleep(5)  # Short scan
            await scanner.stop()
        except Exception as e:
            logger.error(f"State query error: {e}")
        
        return state
    
    def _decode_state_from_advertisement(self, advertisement_data) -> Optional[Dict]:
        """
        Decode light state from BLE advertisement data
        
        BRMesh lights include state in manufacturer data or service data
        """
        if advertisement_data.manufacturer_data:
            for mfr_id, data in advertisement_data.manufacturer_data.items():
                if len(data) >= 7:
                    # Typical format: [ID, R, G, B, W, BRIGHTNESS, POWER]
                    try:
                        return {
                            'state': data[6] == 1 if len(data) > 6 else False,
                            'brightness': data[5] if len(data) > 5 else 255,
                            'rgb': [data[1], data[2], data[3]] if len(data) > 3 else [255, 255, 255]
                        }
                    except IndexError:
                        pass
        
        return None
