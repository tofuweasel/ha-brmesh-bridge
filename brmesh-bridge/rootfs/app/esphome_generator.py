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
    
    def generate_controller_config(self, controller: Dict) -> str:
        """Generate ESPHome YAML config for a controller
        
        In a mesh network, all controllers can control all lights,
        so we include all lights in every controller config.
        """
        controller_name = controller['name'].lower().replace(' ', '-')
        
        config = {
            'esphome': {
                'name': controller_name,
                'platform': 'esp32',
                'board': 'esp32dev'
            },
            'wifi': {
                'ssid': '!secret wifi_ssid',
                'password': '!secret wifi_password',
                'manual_ip': {
                    'static_ip': controller.get('ip_address', '10.1.10.154'),
                    'gateway': '!secret gateway',
                    'subnet': '!secret subnet'
                }
            },
            'api': {
                'encryption': {
                    'key': '!secret api_encryption_key'
                }
            },
            'ota': {
                'password': '!secret ota_password'
            },
            'logger': {
                'level': 'INFO'
            },
            'external_components': [{
                'source': 'github://scross01/esphome-fastcon@main',
                'components': ['fastcon'],
                'refresh': '0s'  # Cache the component to avoid repeated clones
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
        
        return yaml.dump(config, default_flow_style=False, sort_keys=False)
    
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
        """Save secrets.yaml template if it doesn't exist"""
        filepath = os.path.join(self.config_dir, 'secrets.yaml')
        
        if not os.path.exists(filepath):
            try:
                with open(filepath, 'w') as f:
                    f.write(self.generate_secrets_template())
                logger.info(f"Generated secrets template: {filepath}")
            except Exception as e:
                logger.error(f"Failed to write secrets template: {e}")
    
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
