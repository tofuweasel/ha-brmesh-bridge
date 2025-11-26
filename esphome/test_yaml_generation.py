#!/usr/bin/env python3
"""
Test script to verify optimized YAML generation
"""
import sys
import os

# Add the addon app directory to the path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brmesh-bridge', 'rootfs', 'app'))

from esphome_generator import ESPHomeConfigGenerator

class MockBridge:
    """Mock bridge object for testing"""
    def __init__(self):
        self.config = {
            'mesh_key': '30323336',
            'use_optimized_fork': True,
            'generate_esphome_configs': True
        }
        self.lights = {}  # Start with no lights
        self.controllers = []

# Test optimized mode with no lights
bridge = MockBridge()
generator = ESPHomeConfigGenerator(bridge)

controller = {
    'name': 'BRMesh Bridge',
    'ip_address': '192.168.1.100'
}

print("=" * 80)
print("Testing OPTIMIZED mode with 0 lights:")
print("=" * 80)
yaml_output = generator.generate_controller_config(controller, use_optimized=True)
print(yaml_output)

print("\n" + "=" * 80)
print("Testing STANDARD mode with 3 lights:")
print("=" * 80)

# Add some lights for standard mode test
bridge.lights = {
    1: {'name': 'Living Room', 'color_interlock': True, 'supports_cwww': False},
    2: {'name': 'Kitchen', 'color_interlock': True, 'supports_cwww': False},
    3: {'name': 'Bedroom', 'color_interlock': True, 'supports_cwww': True}
}

yaml_output = generator.generate_controller_config(controller, use_optimized=False)
print(yaml_output)

print("\n" + "=" * 80)
print("Testing OPTIMIZED mode with 3 lights:")
print("=" * 80)
yaml_output = generator.generate_controller_config(controller, use_optimized=True)
print(yaml_output)
