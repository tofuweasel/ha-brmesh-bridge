#!/usr/bin/env python3
"""
ESPHome Configuration Generator for BRMesh Controllers
Generates YAML configs that Home Assistant can use as source of truth
"""
import os
import logging
from typing import Dict, List
import yaml

logger = logging.getLogger(__name__)

class ESPHomeConfigGenerator:
    def __init__(self, bridge):
        self.bridge = bridge
        self.config_dir = "/config/esphome"
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
    
    def _get_yaml_handler(self):
        """Get ruamel.yaml instance configured to preserve comments"""
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        return yaml
    
    def generate_controller_config(self, controller: Dict, use_optimized: bool = True) -> str:
        """Generate ESPHome YAML config for a controller
        
        In a mesh network, all controllers can control all lights,
        so we include all lights in every controller config.
        
        Args:
            controller: Controller configuration dictionary
            use_optimized: Use optimized fork with command deduplication (default: True)
        """
        controller_name = controller['name'].lower().replace(' ', '-')
        
        # Base WiFi config with DHCP by default
        wifi_config = {
            'ssid': '!secret wifi_ssid',
            'password': '!secret wifi_password',
            'ap': {
                'ssid': f'{controller_name.title()}-Fallback',
                'password': 'brmesh123'
            }
        }
        
        # Only add static IP if explicitly provided
        if controller.get('ip_address'):
            wifi_config['use_address'] = controller['ip_address']
        else:
            # Use mDNS hostname by default
            wifi_config['use_address'] = f'{controller_name}.local'
        
        # Bridge firmware version (independent of addon version)
        BRIDGE_FIRMWARE_VERSION = "1.0.0"
        
        config = {
            'substitutions': {
                'bridge_version': BRIDGE_FIRMWARE_VERSION
            },
            'esphome': {
                'name': controller_name,
                'friendly_name': controller['name'],
                'comment': f'ESP BLE Bridge v{BRIDGE_FIRMWARE_VERSION}'
            },
            'esp32': {
                'board': 'esp32dev',
                'framework': {
                    'type': 'arduino'
                }
            },
            'logger': {
                'level': 'DEBUG'
            },
            'api': {
                'encryption': {
                    'key': '!secret api_encryption_key'
                }
            },
            'ota': [{
                'platform': 'esphome',
                'password': '!secret ota_password'
            }],
            'wifi': wifi_config,
            'captive_portal': {},
            'mdns': {
                'disabled': False
            },
            'web_server': {
                'port': 80,
                'version': 2,
                'local': True
            }
        }
        
        # Use optimized fork with command deduplication if enabled
        if use_optimized:
            config['esp32_ble_tracker'] = {
                'scan_parameters': {
                    'interval': '320ms',
                    'window': '300ms',
                    'active': True,
                    'continuous': True
                },
                'on_ble_advertise': [{
                    'then': [{
                        'lambda': """
// Log all BLE advertisements for debugging
ESP_LOGD("ble_scan", "Device: %s RSSI: %d", x.address_str().c_str(), x.get_rssi());

// Check manufacturer data
auto mfg_datas = x.get_manufacturer_datas();
if (!mfg_datas.empty()) {
  for (auto mfg_data : mfg_datas) {
    uint16_t uuid = mfg_data.uuid.get_uuid().uuid.uuid16;
    ESP_LOGD("ble_scan", "  Manufacturer UUID: 0x%04x", uuid);
    
    // BRMesh devices use manufacturer ID 0xf0ff
    if (uuid == 0xf0ff || uuid == 0xfff0) {
      ESP_LOGI("ble", "BRMesh device found: %s (RSSI: %d)", 
               x.address_str().c_str(), x.get_rssi());
      
      // Log raw manufacturer data
      std::string hex = "";
      for (auto byte : mfg_data.data) {
        char buf[3];
        sprintf(buf, "%02x", byte);
        hex += buf;
      }
      ESP_LOGI("pairing", "Manufacturer data: %s", hex.c_str());
      break;
    }
  }
}
                        """
                    }]
                }]
            }
            config['esp32_ble_server'] = {}
            config['external_components'] = [{
                'source': 'github://tofuweasel/esphome-fastcon@optimized',
                'components': ['fastcon'],
                'refresh': '0s'
            }]
            config['switch'] = [
                {
                    'platform': 'template',
                    'name': 'Pairing Mode',
                    'id': 'pairing_mode',
                    'icon': 'mdi:bluetooth-connect',
                    'optimistic': True,
                    'restore_mode': 'ALWAYS_OFF',
                    'turn_on_action': [{
                        'logger.log': {
                            'format': '=== PAIRING MODE ENABLED ===',
                            'level': 'WARN'
                        }
                    }, {
                        'logger.log': {
                            'format': 'Factory reset a light to pair it',
                            'level': 'INFO'
                        }
                    }],
                    'turn_off_action': [{
                        'logger.log': {
                            'format': 'Pairing mode disabled',
                            'level': 'INFO'
                        }
                    }]
                },
                {
                    'platform': 'template',
                    'name': 'Music Mode',
                    'id': 'music_mode',
                    'icon': 'mdi:music',
                    'optimistic': True,
                    'restore_mode': 'ALWAYS_OFF',
                    'turn_on_action': [{
                        'logger.log': {
                            'level': 'INFO',
                            'format': 'Music reactive mode enabled'
                        }
                    }],
                    'turn_off_action': [{
                        'logger.log': {
                            'level': 'INFO',
                            'format': 'Music reactive mode disabled'
                        }
                    }]
                }
            ]
        else:
            config['esp32_ble_server'] = {}
            config['external_components'] = [{
                'source': 'github://scross01/esphome-fastcon@dev',
                'components': ['fastcon']
            }]
        
        config['fastcon'] = {
            'id': 'fastcon_controller',
            'mesh_key': '!secret mesh_key'
        }
        config['light'] = []
        
        # Add ALL lights - this is a mesh network after all!
        # If no lights configured yet, add them from config
        lights_to_add = []
        
        if use_optimized and not self.bridge.lights:
            # Optimized mode starts with 0 lights - user pairs them manually
            # Lights should be added to the config as they're paired
            pass
        elif self.bridge.lights:
            # Use configured lights
            for light_id, light in self.bridge.lights.items():
                lights_to_add.append({
                    'light_id': light_id,
                    'name': light['name'],
                    'color_interlock': light.get('color_interlock', True),
                    'supports_cwww': light.get('supports_cwww', False)
                })
        else:
            # Standard mode - no lights configured yet, add default count
            num_lights = controller.get('num_lights', 15)  # Default to 15
            for i in range(1, num_lights + 1):
                lights_to_add.append({
                    'light_id': i,
                    'name': f'BRMesh Light {i:02d}',
                    'color_interlock': True,
                    'supports_cwww': False
                })
        
        # Generate light configs
        for light_data in lights_to_add:
            light_id = light_data['light_id']
            light_config = {
                'platform': 'fastcon',
                'id': f"brmesh_light_{light_id:02d}",
                'name': light_data['name'],
                'light_id': light_id,
                'color_interlock': light_data['color_interlock']
            }
            
            # Only add throttle in standard mode - optimized mode has it built-in
            if not use_optimized:
                light_config['throttle'] = '300ms'  # Prevent command queue overflow
            
            if light_data.get('supports_cwww'):
                light_config['supports_cwww'] = True
            
            config['light'].append(light_config)
        
        # Add monitoring sensors
        text_sensors = [
            {
                'platform': 'wifi_info',
                'ip_address': {'name': 'IP Address'},
                'mac_address': {'name': 'MAC Address'},
                'ssid': {'name': 'WiFi SSID'}
            },
            {
                'platform': 'version',
                'name': 'ESPHome Version'
            },
            {
                'platform': 'template',
                'name': 'Bridge Firmware Version',
                'id': 'bridge_firmware_version',
                'icon': 'mdi:tag',
                'lambda': f'return {{\"{BRIDGE_FIRMWARE_VERSION}\"}};'
            }
        ]
        
        config['sensor'] = [
            {
                'platform': 'wifi_signal',
                'name': 'WiFi Signal',
                'update_interval': '60s'
            },
            {
                'platform': 'uptime',
                'name': 'Uptime',
                'update_interval': '60s'
            }
        ]
        
        buttons = [
            {
                'platform': 'restart',
                'name': 'Restart ESP32',
                'icon': 'mdi:restart'
            },
            {
                'platform': 'safe_mode',
                'name': 'Safe Mode Boot',
                'icon': 'mdi:security'
            }
        ]
        
        config['binary_sensor'] = [
            {
                'platform': 'status',
                'name': 'ESP32 Status'
            }
        ]
        
        # Add extra features in optimized mode
        if use_optimized:
            # Music mode controls
            config['number'] = [
                {
                    'platform': 'template',
                    'name': 'Music Sensitivity',
                    'id': 'music_sensitivity',
                    'icon': 'mdi:volume-high',
                    'min_value': 0.1,
                    'max_value': 5.0,
                    'step': 0.1,
                    'initial_value': 1.0,
                    'mode': 'slider',
                    'optimistic': True
                },
                {
                    'platform': 'template',
                    'name': 'Music Update Rate (Hz)',
                    'id': 'music_update_rate',
                    'icon': 'mdi:timer',
                    'min_value': 5,
                    'max_value': 30,
                    'step': 1,
                    'initial_value': 10,
                    'mode': 'slider',
                    'optimistic': True
                }
            ]
            
            config['select'] = [
                {
                    'platform': 'template',
                    'name': 'Music Color Mode',
                    'id': 'music_color_mode',
                    'icon': 'mdi:palette',
                    'optimistic': True,
                    'options': ['RGB Frequency', 'Amplitude', 'Rainbow Cycle', 'Bass Pulse'],
                    'initial_option': 'RGB Frequency'
                }
            ]
        
        config['text_sensor'] = text_sensors
        config['button'] = buttons
        
        # Use PyYAML with custom representer that doesn't quote !secret tags
        import yaml
        from io import StringIO
        
        # Custom representer for !secret tags
        def secret_representer(dumper, data):
            if isinstance(data, str) and data.startswith('!secret '):
                # Return the tag without quotes
                return dumper.represent_scalar('tag:yaml.org,2002:str', data, style='')
            return dumper.represent_str(data)
        
        # Register custom representer
        yaml.add_representer(str, secret_representer)
        
        # Convert to YAML without quotes on !secret tags
        yaml_output = yaml.dump(config, default_flow_style=False, sort_keys=False, allow_unicode=True)
        
        # Remove quotes around !secret tags that might still appear
        import re
        yaml_output = re.sub(r"'(!secret [^']+)'", r'\1', yaml_output)
        yaml_output = re.sub(r'"(!secret [^"]+)"', r'\1', yaml_output)
        
        # Add helpful comment for optimized mode if no lights configured
        if use_optimized and not lights_to_add:
            light_template = """
# To add lights after pairing, uncomment and modify the template below:
# - platform: fastcon
#   id: brmesh_light_01
#   name: "Living Room Light"
#   light_id: 1
#   color_interlock: true
#   # supports_cwww: false  # Set to true for tunable white lights

# Example: Add more lights by incrementing light_id
# - platform: fastcon
#   id: brmesh_light_02
#   name: "Kitchen Light"
#   light_id: 2
#   color_interlock: true
"""
            # Insert the template comment after the light: [] line
            yaml_output = yaml_output.replace('light: []', 'light: []' + light_template)
        
        return yaml_output
    
    def generate_all_configs(self) -> Dict[str, str]:
        """Generate configs for all controllers"""
        configs = {}
        
        # Check if optimized mode is enabled (default: True)
        use_optimized = self.bridge.config.get('use_optimized_fork', True)
        
        for controller in self.bridge.controllers:
            controller_name = controller['name']
            
            # Generate config with ALL lights (mesh network!)
            yaml_config = self.generate_controller_config(controller, use_optimized=use_optimized)
            configs[controller_name] = yaml_config
            
            # Save to file
            filename = f"{controller_name.lower().replace(' ', '-')}.yaml"
            filepath = os.path.join(self.config_dir, filename)
            
            try:
                with open(filepath, 'w') as f:
                    f.write(yaml_config)
                logger.info(f"Generated ESPHome config: {filepath}")
            except Exception as e:
                logger.error(f"Failed to write config {filepath}: {e}")
        
        return configs
    
    def generate_secrets_template(self) -> str:
        """Generate secrets.yaml template"""
        secrets = {
            'wifi_ssid': 'Your_WiFi_SSID',
            'wifi_password': 'your_wifi_password',
            'gateway': '192.168.1.1',
            'subnet': '255.255.255.0',
            'api_encryption_key': 'generate_with_esphome',
            'ota_password': 'your_ota_password'
        }
        
        return yaml.dump(secrets, default_flow_style=False)
    
    def save_secrets_template(self):
        """Generate OTA/API secrets in /config/esphome/secrets.yaml if needed
        
        WiFi secrets are managed in /config/secrets.yaml (Home Assistant's main secrets file)
        This only creates OTA and API encryption keys if they don't exist.
        """
        from ruamel.yaml import YAML
        from ruamel.yaml.scalarstring import PlainScalarString
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        
        # Use Home Assistant's main secrets file
        ha_secrets_path = '/config/secrets.yaml'
        
        logger.info(f"🔍 Checking for secrets file at: {ha_secrets_path}")
        file_exists = os.path.exists(ha_secrets_path)
        logger.info(f"📁 File exists: {file_exists}")
        
        if not file_exists:
            # Create basic secrets file if it doesn't exist
            try:
                logger.info(f"📝 Creating new secrets file...")
                api_key = self._generate_random_key()
                ota_pass = self._generate_random_password()
                secrets = {
                    'wifi_ssid': 'Your_WiFi_SSID',
                    'wifi_password': 'your_wifi_password',
                    'gateway': '192.168.1.1',
                    'subnet': '255.255.255.0',
                    'api_encryption_key': api_key,
                    'ota_password': ota_pass,
                    'mesh_key': self.bridge.config.get('mesh_key', '30323336')
                }
                yaml_handler = self._get_yaml_handler()
                with open(ha_secrets_path, 'w') as f:
                    yaml_handler.dump(secrets, f)
                logger.info(f"✅ Created /config/secrets.yaml with generated keys")
                logger.info(f"🔑 API key length: {len(api_key)}, valid base64: {self._is_valid_base64_key(api_key)}")
            except Exception as e:
                logger.error(f"Failed to create secrets file: {e}", exc_info=True)
        else:
            logger.info(f"📖 File exists, validating existing keys...")
            # Check if OTA/API keys exist, add them if missing or invalid
            try:
                # Just load the file directly with ruamel.yaml
                # It will handle duplicate keys by keeping the last one
                with open(ha_secrets_path, 'r') as f:
                    secrets = yaml.load(f) or {}
                
                logger.info(f"📋 Loaded {len(secrets)} keys from secrets.yaml")
                logger.info(f"🔑 Keys present: {list(secrets.keys())}")
                
                updated = False
                # Generate or replace invalid API encryption key
                api_key = secrets.get('api_encryption_key', '')
                if not api_key or not self._is_valid_base64_key(api_key):
                    logger.info(f"🔑 Regenerating invalid api_encryption_key (was: {api_key[:20] if api_key else 'missing'}...)")
                    # Use PlainScalarString to ensure no quotes are added
                    secrets['api_encryption_key'] = PlainScalarString(self._generate_random_key())
                    updated = True
                else:
                    logger.info(f"✅ API encryption key is valid (length: {len(api_key)}) - preserving existing key")
                    # Preserve existing valid key, just ensure it's a PlainScalarString
                    if not isinstance(api_key, PlainScalarString):
                        secrets['api_encryption_key'] = PlainScalarString(str(api_key))
                        updated = True
                
                # Generate or replace invalid OTA password
                ota_pass = secrets.get('ota_password', '')
                if not ota_pass or ota_pass == 'your_ota_password' or len(ota_pass) < 8:
                    logger.info(f"🔑 Regenerating invalid ota_password")
                    secrets['ota_password'] = PlainScalarString(self._generate_random_password())
                    updated = True
                else:
                    logger.info(f"✅ OTA password is valid")
                    # Ensure existing valid password is also plain scalar
                    if not isinstance(ota_pass, PlainScalarString):
                        secrets['ota_password'] = PlainScalarString(str(ota_pass))
                        updated = True
                
                # Ensure mesh_key is present (from bridge config)
                if 'mesh_key' not in secrets and self.bridge.config.get('mesh_key'):
                    logger.info(f"🔑 Adding mesh_key to secrets")
                    secrets['mesh_key'] = PlainScalarString(self.bridge.config.get('mesh_key'))
                    updated = True
                
                if updated:
                    yaml_handler = self._get_yaml_handler()
                    with open(ha_secrets_path, 'w') as f:
                        yaml_handler.dump(secrets, f)
                    logger.info(f"✅ Updated /config/secrets.yaml with missing keys")
                    
                    # Also copy to ESPHome directory so ESPHome can find it
                    esphome_secrets_path = '/config/esphome/secrets.yaml'
                    try:
                        os.makedirs(os.path.dirname(esphome_secrets_path), exist_ok=True)
                        with open(esphome_secrets_path, 'w') as f:
                            yaml_handler.dump(secrets, f)
                        logger.info(f"✅ Copied secrets to /config/esphome/secrets.yaml for ESPHome")
                    except Exception as copy_error:
                        logger.error(f"Failed to copy secrets to esphome directory: {copy_error}")
            except Exception as e:
                logger.error(f"Failed to update secrets: {e}")
    
    def _is_valid_base64_key(self, key: str) -> bool:
        """Check if a string is valid base64 and appropriate length for encryption"""
        import base64
        try:
            # Must be at least 32 characters (24 bytes base64 encoded)
            if len(key) < 32:
                return False
            # Try to decode as base64
            decoded = base64.b64decode(key, validate=True)
            # Should be at least 16 bytes for a valid encryption key
            return len(decoded) >= 16
        except Exception:
            return False
    
    def _generate_random_key(self) -> str:
        """Generate a random 32-byte base64 key for API encryption"""
        import secrets
        import base64
        return base64.b64encode(secrets.token_bytes(32)).decode('ascii')
    
    def _generate_random_password(self) -> str:
        """Generate a random password for OTA"""
        import secrets
        import string
        alphabet = string.ascii_letters + string.digits
        return ''.join(secrets.choice(alphabet) for _ in range(16))
    
    def sync_configs(self):
        """Main entry point - generate all configs"""
        if not self.bridge.config.get('generate_esphome_configs', True):
            logger.info("ESPHome config generation disabled")
            return
        
        logger.info("Generating ESPHome configurations...")
        configs = self.generate_all_configs()
        self.save_secrets_template()
        
        logger.info(f"Generated {len(configs)} ESPHome controller configs")
        return configs
