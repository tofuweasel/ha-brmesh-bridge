#!/usr/bin/env python3
"""
BRMesh Bridge - Comprehensive light management system
- Dynamic discovery and registration
- ESPHome config generation
- BRMesh app sync
- NSPanel UI
- Web dashboard
"""
import asyncio
import json
import logging
import os
import sys
from typing import Dict, List
import paho.mqtt.client as mqtt
from bleak import BleakScanner
import struct
import threading
from effects import BRMeshEffects
from web_ui import WebUI, app
from esphome_generator import ESPHomeConfigGenerator
from esphome_builder import ESPHomeBuilder
from ble_discovery import BRMeshDiscovery
from app_importer import BRMeshAppImporter
from nspanel_ui import NSPanelUIGenerator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s:%(name)s:%(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

class BRMeshBridge:
    def __init__(self):
        # Initialize lights/controllers before loading config
        self.lights: Dict[int, dict] = {}
        self.controllers: List[dict] = []
        
        self.load_config()
        
        # Configuration from add-on options
        self.mesh_key = self.config.get('mesh_key', '')
        
        # Try to load mesh_key from secrets.yaml if not in config
        if not self.mesh_key:
            try:
                from ruamel.yaml import YAML
                secrets_path = '/config/secrets.yaml'
                if os.path.exists(secrets_path):
                    yaml = YAML()
                    with open(secrets_path, 'r') as f:
                        secrets = yaml.load(f) or {}
                    self.mesh_key = secrets.get('mesh_key', '')
                    if self.mesh_key:
                        self.config['mesh_key'] = self.mesh_key
                        logger.info(f"✅ Loaded mesh_key from secrets.yaml")
            except Exception as e:
                logger.warning(f"Could not load mesh_key from secrets.yaml: {e}")
        
        # Get MQTT credentials from environment (set by Bashio in run script)
        self.mqtt_host = os.getenv('MQTT_HOST', 'core-mosquitto')
        self.mqtt_port = int(os.getenv('MQTT_PORT', '1883'))
        self.mqtt_user = os.getenv('MQTT_USER', '')
        self.mqtt_password = os.getenv('MQTT_PASS', '')
        
        if self.mqtt_user:
            logger.info(f"✅ Got MQTT credentials from Bashio: {self.mqtt_user}@{self.mqtt_host}:{self.mqtt_port}")
        else:
            logger.warning(f"⚠️  No MQTT credentials provided - using anonymous connection")
        self.discovery_enabled = self.config.get('discovery_enabled', True)
        self.mqtt_client = None
        self.effects = None
        self.web_ui = None
        self.esphome_generator = None
        self.esphome_builder = None
        self.ble_discovery = None
        self.app_importer = None
        self.nspanel_ui = None
    
    def load_config(self):
        """Load configured lights and controllers from options"""
        # Set defaults
        self.config = {
            'mesh_key': '',
            'use_addon_mqtt': True,
            'mqtt_host': 'core-mosquitto',
            'mqtt_port': 1883,
            'mqtt_user': '',
            'mqtt_password': '',
            'discovery_enabled': True,
            'generate_esphome_configs': True,
            'enable_ble_discovery': True,
            'enable_nspanel_ui': False,
            'nspanel_entity_id': '',
            'app_config_path': '/share/brmesh_export.json',
            'map_enabled': True,
            'map_latitude': 0.0,
            'map_longitude': 0.0,
            'map_zoom': 19,
            'controllers': [],
            'lights': [],
            'scenes': [],
            'effects': [
                {'name': 'Rainbow', 'enabled': True},
                {'name': 'Color Loop', 'enabled': True},
                {'name': 'Twinkle', 'enabled': True},
                {'name': 'Fire', 'enabled': True}
            ]
        }
        
        try:
            with open('/data/options.json', 'r') as f:
                loaded_config = json.load(f)
                # Merge loaded config with defaults
                self.config.update(loaded_config)
                
                # Load lights
                for light in self.config.get('lights', []):
                    light_id = light['light_id']
                    self.lights[light_id] = {
                        'name': light['name'],
                        'color_interlock': light.get('color_interlock', True),
                        'supports_cwww': light.get('supports_cwww', False),
                        'state': {'state': False, 'brightness': 255, 'rgb': [255, 255, 255]},
                        'location': light.get('location', {'x': None, 'y': None}),
                        'signal_strength': {},
                        'preferred_controller': light.get('preferred_controller')
                    }
                
                # Load controllers
                self.controllers = self.config.get('controllers', [])
                
                # Auto-detect Home Assistant location if not configured
                if not self.config.get('map_latitude') or not self.config.get('map_longitude'):
                    self._detect_ha_location()
                
                logger.info(f"Loaded {len(self.lights)} lights and {len(self.controllers)} controllers from config")
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            import traceback
            logger.error(traceback.format_exc())
    
    def save_config(self):
        """Save configuration back to file"""
        try:
            # Update config object with current light data
            self.config['lights'] = []
            for light_id, light in self.lights.items():
                self.config['lights'].append({
                    'light_id': light_id,
                    'name': light['name'],
                    'color_interlock': light.get('color_interlock', True),
                    'supports_cwww': light.get('supports_cwww', False),
                    'location': light.get('location', {'x': None, 'y': None}),
                    'preferred_controller': light.get('preferred_controller')
                })
            
            self.config['controllers'] = self.controllers
            self.config['mesh_key'] = self.mesh_key
            
            with open('/data/options.json', 'w') as f:
                json.dump(self.config, f, indent=2)
            
            logger.info("Configuration saved")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def setup_mqtt(self):
        """Setup MQTT client"""
        self.mqtt_client = mqtt.Client()
        
        if self.mqtt_user:
            self.mqtt_client.username_pw_set(self.mqtt_user, self.mqtt_password)
        
        self.mqtt_client.on_connect = self.on_mqtt_connect
        self.mqtt_client.on_message = self.on_mqtt_message
        
        try:
            self.mqtt_client.connect(self.mqtt_host, self.mqtt_port, 60)
            logger.info(f"Connected to MQTT broker at {self.mqtt_host}:{self.mqtt_port}")
        except Exception as e:
            logger.error(f"Failed to connect to MQTT: {e}")
            sys.exit(1)
    
    def on_mqtt_connect(self, client, userdata, flags, rc):
        """MQTT connection callback"""
        logger.info("MQTT connected with result code " + str(rc))
        
        # Subscribe to command topics for all lights
        for light_id in self.lights:
            topic = f"homeassistant/light/brmesh_{light_id}/set"
            client.subscribe(topic)
            logger.info(f"Subscribed to {topic}")
        
        # Publish discovery configs
        if self.discovery_enabled:
            self.publish_discovery()
    
    def on_mqtt_message(self, client, userdata, msg):
        """MQTT message callback - handle light commands"""
        try:
            # Parse topic to get light ID
            topic_parts = msg.topic.split('/')
            light_name = topic_parts[2]  # e.g., "brmesh_10"
            light_id = int(light_name.split('_')[1])
            
            if light_id not in self.lights:
                return
            
            # Parse command
            payload = json.loads(msg.payload.decode())
            logger.info(f"Received command for light {light_id}: {payload}")
            
            # Update state
            if 'state' in payload:
                self.lights[light_id]['state']['state'] = payload['state'] == 'ON'
            if 'brightness' in payload:
                self.lights[light_id]['state']['brightness'] = payload['brightness']
            if 'color' in payload:
                rgb = payload['color']
                self.lights[light_id]['state']['rgb'] = [rgb['r'], rgb['g'], rgb['b']]
            
            # Send BLE command
            self.send_ble_command(light_id)
            
            # Publish state
            self.publish_state(light_id)
            
        except Exception as e:
            logger.error(f"Error handling MQTT message: {e}")
    
    def publish_discovery(self):
        """Publish Home Assistant MQTT discovery configs"""
        for light_id, light in self.lights.items():
            unique_id = f"brmesh_{light_id}"
            config = {
                "name": light['name'],
                "unique_id": unique_id,
                "command_topic": f"homeassistant/light/{unique_id}/set",
                "state_topic": f"homeassistant/light/{unique_id}/state",
                "schema": "json",
                "brightness": True,
                "rgb": True,
                "device": {
                    "identifiers": [f"brmesh_bridge"],
                    "name": "BRMesh Bridge",
                    "manufacturer": "ESPHome",
                    "model": "BRMesh Controller"
                }
            }
            
            if light['color_interlock']:
                config['color_mode'] = True
                config['supported_color_modes'] = ['rgb', 'white']
            
            topic = f"homeassistant/light/{unique_id}/config"
            self.mqtt_client.publish(topic, json.dumps(config), retain=True)
            logger.info(f"Published discovery for {light['name']} (ID {light_id})")
    
    def publish_state(self, light_id: int):
        """Publish light state to MQTT"""
        if light_id not in self.lights:
            return
        
        state = self.lights[light_id]['state']
        unique_id = f"brmesh_{light_id}"
        
        payload = {
            "state": "ON" if state['state'] else "OFF",
            "brightness": state['brightness'],
            "color": {
                "r": state['rgb'][0],
                "g": state['rgb'][1],
                "b": state['rgb'][2]
            }
        }
        
        topic = f"homeassistant/light/{unique_id}/state"
        self.mqtt_client.publish(topic, json.dumps(payload))
    
    def set_light_color(self, light_id: int, rgb: tuple, brightness: int = 255, state: bool = True):
        """Set light color directly (used by effects engine)"""
        if light_id not in self.lights:
            return
        
        self.lights[light_id]['state']['state'] = state
        self.lights[light_id]['state']['brightness'] = brightness
        self.lights[light_id]['state']['rgb'] = list(rgb)
        
        self.send_ble_command(light_id)
        self.publish_state(light_id)
    
    def send_ble_command(self, light_id: int):
        """Send BLE command to light (using same protocol as ESPHome fastcon)"""
        if light_id not in self.lights:
            return
        
        state = self.lights[light_id]['state']
        
        # Build BRMesh command packet
        # Format: [CMD_TYPE, LIGHT_ID, R, G, B, W, BRIGHTNESS, ...]
        cmd = 0x22  # Color/state command
        r, g, b = state['rgb']
        brightness = state['brightness']
        power = 0x01 if state['state'] else 0x00
        
        # Build inner payload (12 bytes)
        inner_payload = struct.pack('BBBBBBBBBBBB',
            cmd, light_id,
            r if state['state'] else 0,
            g if state['state'] else 0,
            b if state['state'] else 0,
            0,  # white
            brightness if state['state'] else 0,
            power,
            0, 0, 0, 0  # padding
        )
        
        logger.info(f"Would send BLE command to light {light_id}: {inner_payload.hex()}")
        # TODO: Implement actual BLE broadcast using bleak
    
    def get_controller_signal_map(self, controller_name: str) -> Dict:
        """Get signal strength from controller to all lights"""
        # This would query the ESP32 via MQTT for RSSI values
        # For now, return mock data
        signal_map = {}
        for light_id in self.lights.keys():
            signal_map[light_id] = {
                'rssi': -60,  # Mock RSSI value
                'quality': 'good'
            }
        return signal_map
    
    def scan_for_new_lights(self) -> List[dict]:
        """Scan BRMesh network for new lights"""
        # This would use ADB or BLE scanning
        # For now, return empty list
        return []
    
    async def scan_for_lights_async(self):
        """Scan for BRMesh devices (optional discovery feature)"""
        if not self.discovery_enabled:
            return
        
        logger.info("Scanning for BRMesh devices...")
        # TODO: Implement BLE scanning to detect lights
        # This would listen for BRMesh advertisements and auto-discover light IDs
    
    async def run_async(self):
        """Async initialization and background tasks"""
        # Initialize BLE discovery if enabled
        if self.config.get('enable_ble_discovery', True):
            self.ble_discovery = BRMeshDiscovery(self)
            logger.info("BLE discovery enabled")
            
            # Run initial scan if configured
            if self.config.get('auto_discover_on_start', False):
                logger.info("Running initial device discovery...")
                discovered = await self.ble_discovery.auto_discover_and_register(duration=30)
                logger.info(f"Auto-discovered {len(discovered)} new devices")
        
        # Initialize app importer
        self.app_importer = BRMeshAppImporter(self)
        
        # Try to import from app export if path configured
        app_config_path = self.config.get('app_config_path')
        if app_config_path and os.path.exists(app_config_path):
            logger.info(f"Importing configuration from {app_config_path}")
            imported = self.app_importer.import_from_json_export(app_config_path)
            if imported:
                self.app_importer.apply_imported_config(imported)
        
        # Initialize NSPanel UI if enabled
        if self.config.get('enable_nspanel_ui', False):
            self.nspanel_ui = NSPanelUIGenerator(self)
            self.nspanel_ui.initialize_nspanel_ui()
            logger.info("NSPanel UI initialized")
        
        # Generate ESPHome configs if enabled
        if self.config.get('generate_esphome_configs', True):
            self.esphome_generator = ESPHomeConfigGenerator(self)
            self.esphome_generator.sync_configs()
            logger.info("ESPHome configurations generated")
        
        # Initialize ESPHome builder for compiling/flashing
        self.esphome_builder = ESPHomeBuilder(self)
        logger.info("🔨 ESPHome builder initialized")
        
        # Keep running and periodically refresh
        try:
            while True:
                await asyncio.sleep(300)  # Every 5 minutes
                
                # Optionally sync device names from app
                if self.config.get('auto_sync_names', False) and self.app_importer:
                    self.app_importer.sync_device_names_from_app()
                
                # Regenerate ESPHome configs if lights changed
                if self.esphome_generator:
                    self.esphome_generator.sync_configs()
                
        except KeyboardInterrupt:
            logger.info("Shutting down...")
    
    def run(self):
        """Main run loop"""
        logger.info("=" * 80)
        logger.info("=" * 80)
        logger.info("🚀 BRMesh Bridge v0.17.3 - Starting Up (Bashio)")
        logger.info("=" * 80)
        logger.info(f"📡 Mesh Key: {self.mesh_key if self.mesh_key else '(not configured - use Web UI)'}")
        logger.info(f"🔌 MQTT Broker: {self.mqtt_host}:{self.mqtt_port}")
        logger.info(f"👤 MQTT User: {self.mqtt_user if self.mqtt_user else '(anonymous)'}")
        logger.info("=" * 80)
        
        self.setup_mqtt()
        self.mqtt_client.loop_start()
        
        # Initialize effects engine
        self.effects = BRMeshEffects(self)
        logger.info("✨ Effects engine initialized")
        
        # Initialize web UI
        self.web_ui = WebUI(self)
        
        # Start web server in separate thread
        web_thread = threading.Thread(
            target=self.web_ui.run,
            kwargs={'host': '0.0.0.0', 'port': 8099}
        )
        web_thread.daemon = True
        web_thread.start()
        
        logger.info("🌐 Web UI available at http://localhost:8099")
        logger.info("=" * 80)
        logger.info("✅ BRMesh Bridge Ready!")
        logger.info(f"  💡 {len(self.lights)} lights configured")
        logger.info(f"  🎮 {len(self.controllers)} controllers configured")
        logger.info(f"  📶 BLE Discovery: {'Enabled' if self.config.get('enable_ble_discovery') else 'Disabled'}")
        logger.info(f"  ⚙️  ESPHome Configs: {'Enabled' if self.config.get('generate_esphome_configs') else 'Disabled'}")
        logger.info(f"  📱 NSPanel UI: {'Enabled' if self.config.get('enable_nspanel_ui') else 'Disabled'}")
        logger.info("=" * 80)
        logger.info("📋 Copy logs from the line above (80 = characters) for troubleshooting")
        logger.info("=" * 80)
        
        # Run async tasks
        try:
            asyncio.run(self.run_async())
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.mqtt_client.loop_stop()
            self.mqtt_client.disconnect()
    
    def _detect_ha_location(self):
        """Auto-detect Home Assistant's configured location"""
        try:
            # Try to read from Home Assistant API
            supervisor_token = os.getenv('SUPERVISOR_TOKEN')
            if not supervisor_token:
                logger.debug("No supervisor token available for location detection")
                return
            
            import requests
            headers = {
                'Authorization': f'Bearer {supervisor_token}',
                'Content-Type': 'application/json'
            }
            
            # Get Home Assistant config
            response = requests.get(
                'http://supervisor/core/api/config',
                headers=headers,
                timeout=5
            )
            
            if response.status_code == 200:
                ha_config = response.json()
                latitude = ha_config.get('latitude')
                longitude = ha_config.get('longitude')
                
                if latitude and longitude:
                    self.config['latitude'] = latitude
                    self.config['longitude'] = longitude
                    logger.info(f"✅ Auto-detected Home Assistant location: {latitude}, {longitude}")
                    
                    # Save to options.json
                    try:
                        options_path = '/data/options.json'
                        with open(options_path, 'r') as f:
                            options = json.load(f)
                        options['latitude'] = latitude
                        options['longitude'] = longitude
                        with open(options_path, 'w') as f:
                            json.dump(options, f, indent=2)
                        logger.info("📍 Saved auto-detected location to configuration")
                    except Exception as e:
                        logger.warning(f"Could not save location to config: {e}")
                else:
                    logger.info("No location configured in Home Assistant")
            else:
                logger.debug(f"Could not fetch HA config: HTTP {response.status_code}")
        except Exception as e:
            logger.debug(f"Could not auto-detect Home Assistant location: {e}")


if __name__ == '__main__':
    bridge = BRMeshBridge()
    bridge.run()
