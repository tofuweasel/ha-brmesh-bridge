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
    
    def _get_yaml_handler(self):
        """Get ruamel.yaml instance configured to preserve comments"""
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        return yaml
        self.config_dir = "/config/esphome"
        
        # Create directory if it doesn't exist
        os.makedirs(self.config_dir, exist_ok=True)
    
    def generate_controller_config(self, controller: Dict) -> str:
        """Generate ESPHome YAML config for a controller
        
        In a mesh network, all controllers can control all lights,
        so we include all lights in every controller config.
        """
        controller_name = controller['name'].lower().replace(' ', '-')
        
        # Base WiFi config with DHCP by default
        wifi_config = {
            'ssid': '!secret wifi_ssid',
            'password': '!secret wifi_password'
        }
        
        # Only add static IP if explicitly provided
        if controller.get('ip_address'):
            wifi_config['manual_ip'] = {
                'static_ip': controller['ip_address'],
                'gateway': '!secret gateway',
                'subnet': '!secret subnet'
            }
        
        config = {
            'esphome': {
                'name': controller_name
            },
            'esp32': {
                'board': 'esp32dev',
                'framework': {
                    'type': 'arduino'
                }
            },
            'wifi': wifi_config,
            'api': {
                'encryption': {
                    'key': '!secret api_encryption_key'
                }
            },
            'ota': [{
                'platform': 'esphome',
                'password': '!secret ota_password'
            }],
            'logger': {
                'level': 'INFO'
            },
            'external_components': [{
                'source': '/app/external_components',
                'components': ['fastcon']
            }],
            'esp32_ble_server': {},
            'fastcon': {
                'mesh_key': self.bridge.config.get('mesh_key', '30323336')
            },
            'light': []
        }
        
        # Add ALL lights - this is a mesh network after all!
        for light_id, light in self.bridge.lights.items():
            light_config = {
                'platform': 'fastcon',
                'id': f"brmesh_light_{light_id}",
                'name': light['name'],
                'light_id': light_id,
                'color_interlock': light.get('color_interlock', True)
            }
            
            if light.get('supports_cwww'):
                light_config['supports_cwww'] = True
            
            config['light'].append(light_config)
        
        # Use custom YAML dumper that doesn't quote !secret tags
        from ruamel.yaml import YAML
        from ruamel.yaml.scalarstring import PlainScalarString
        from io import StringIO
        
        # Convert !secret strings to plain scalars so they don't get quoted
        def convert_secrets(obj):
            if isinstance(obj, dict):
                return {k: convert_secrets(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_secrets(item) for item in obj]
            elif isinstance(obj, str) and obj.startswith('!secret '):
                return PlainScalarString(obj)
            else:
                return obj
        
        config = convert_secrets(config)
        
        yaml_handler = YAML()
        yaml_handler.default_flow_style = False
        stream = StringIO()
        yaml_handler.dump(config, stream)
        return stream.getvalue()
    
    def generate_all_configs(self) -> Dict[str, str]:
        """Generate configs for all controllers"""
        configs = {}
        
        for controller in self.bridge.controllers:
            controller_name = controller['name']
            
            # Generate config with ALL lights (mesh network!)
            yaml_config = self.generate_controller_config(controller)
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
                    'ota_password': ota_pass
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
                # Read as text first to check for duplicates
                with open(ha_secrets_path, 'r') as f:
                    content = f.read()
                
                # Remove duplicate keys by keeping only the last occurrence
                lines = content.split('\n')
                seen_keys = {}
                for i, line in enumerate(lines):
                    if ':' in line and not line.strip().startswith('#'):
                        key = line.split(':')[0].strip()
                        if key:
                            seen_keys[key] = i
                
                # Check if we have duplicates
                duplicate_count = len(lines) - len([l for l in lines if not l.strip() or l.strip().startswith('#') or ':' not in l]) - len(seen_keys)
                if duplicate_count > 0:
                    logger.warning(f"⚠️  Found {duplicate_count} duplicate keys, cleaning up...")
                    # Rebuild file with only unique keys (last occurrence wins)
                    deduplicated_lines = []
                    for i, line in enumerate(lines):
                        if ':' in line and not line.strip().startswith('#'):
                            key = line.split(':')[0].strip()
                            if key and seen_keys.get(key) == i:
                                deduplicated_lines.append(line)
                        else:
                            deduplicated_lines.append(line)
                    content = '\n'.join(deduplicated_lines)
                    # Write cleaned file back
                    with open(ha_secrets_path, 'w') as f:
                        f.write(content)
                    logger.info(f"✅ Removed duplicate keys from secrets.yaml")
                
                # Now parse the cleaned content
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
                    logger.info(f"✅ API encryption key is valid (length: {len(api_key)})")
                    logger.info(f"🔍 Key type: {type(api_key).__name__}")
                    logger.info(f"🔍 Key repr: {repr(api_key)}")
                    # ALWAYS regenerate to ensure proper formatting (quotes issue)
                    # Once ESPHome accepts the key, we can switch back to preserving it
                    logger.warning(f"⚠️  Regenerating key to ensure proper formatting (ESPHome quote issue)")
                    secrets['api_encryption_key'] = PlainScalarString(self._generate_random_key())
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
                
                if updated:
                    # Deduplicate secrets before saving
                    seen_keys = set()
                    deduplicated = {}
                    for key in secrets:
                        if key not in seen_keys:
                            deduplicated[key] = secrets[key]
                            seen_keys.add(key)
                    
                    yaml_handler = self._get_yaml_handler()
                    with open(ha_secrets_path, 'w') as f:
                        yaml_handler.dump(deduplicated, f)
                    logger.info(f"✅ Updated /config/secrets.yaml with missing keys (deduplicated {len(secrets) - len(deduplicated)} duplicate entries)")
                    
                    # Also copy to ESPHome directory so ESPHome can find it
                    esphome_secrets_path = '/config/esphome/secrets.yaml'
                    try:
                        os.makedirs(os.path.dirname(esphome_secrets_path), exist_ok=True)
                        with open(esphome_secrets_path, 'w') as f:
                            yaml_handler.dump(deduplicated, f)
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
