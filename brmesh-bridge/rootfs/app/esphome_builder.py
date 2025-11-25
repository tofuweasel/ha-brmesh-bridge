#!/usr/bin/env python3
"""
ESPHome Builder - Compile and flash ESP32 controllers directly from the add-on
"""
import os
import subprocess
import logging
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class ESPHomeBuilder:
    """Build and flash ESP32 controllers using ESPHome"""
    
    def __init__(self, bridge):
        self.bridge = bridge
        self.build_dir = "/config/esphome"
        self.secrets_file = os.path.join(self.build_dir, "secrets.yaml")
        
        # Ensure build directory exists
        os.makedirs(self.build_dir, exist_ok=True)
    
    def compile_firmware(self, controller_name: str) -> Dict:
        """Compile firmware for a controller
        
        Args:
            controller_name: Name of the controller (used for filename)
            
        Returns:
            Dict with status and firmware path
        """
        yaml_file = os.path.join(self.build_dir, f"{controller_name.lower().replace(' ', '-')}.yaml")
        
        if not os.path.exists(yaml_file):
            return {'success': False, 'error': f'Config file not found: {yaml_file}'}
        
        try:
            logger.info(f"🔨 Compiling firmware for {controller_name}...")
            logger.info(f"📄 Config file: {yaml_file}")
            logger.info("⏳ This may take 5-10 minutes for first build (downloading external components)...")
            
            # Run ESPHome compile command (no --verbose flag, it's not supported in this version)
            result = subprocess.run(
                ['esphome', 'compile', yaml_file],
                capture_output=True,
                text=True,
                timeout=900,  # 15 minute timeout for first build
                env={**os.environ, 'PLATFORMIO_CORE_DIR': '/config/.platformio'}
            )
            
            # Log full output for debugging
            if result.stdout:
                logger.info(f"ESPHome stdout:\n{result.stdout}")
            if result.stderr:
                logger.error(f"ESPHome stderr:\n{result.stderr}")
            
            if result.returncode == 0:
                # Find the compiled firmware binary
                firmware_path = self._find_firmware_binary(controller_name)
                logger.info(f"✅ Compilation successful: {firmware_path}")
                return {
                    'success': True,
                    'firmware_path': firmware_path,
                    'output': result.stdout
                }
            else:
                logger.error(f"❌ Compilation failed with return code: {result.returncode}")
                
                # Parse error for helpful message
                error_msg = result.stderr
                if "github.com" in error_msg or "Cloning" in error_msg or "git" in error_msg.lower():
                    error_msg = f"Failed to download external component from GitHub. This may be a temporary network issue. Full error: {error_msg}"
                
                return {
                    'success': False,
                    'error': error_msg,
                    'output': result.stdout,
                    'stderr': result.stderr
                }
                
        except subprocess.TimeoutExpired:
            logger.error("⏱️ Compilation timeout")
            return {'success': False, 'error': 'Compilation timeout (15 minutes). First build may take longer.'}
        except Exception as e:
            logger.error(f"❌ Compilation error: {e}")
            return {'success': False, 'error': str(e)}
    
    def flash_firmware(self, controller_name: str, port: str = 'auto') -> Dict:
        """Flash firmware to ESP32
        
        Args:
            controller_name: Name of the controller
            port: Serial port (e.g., /dev/ttyUSB0) or 'auto' for auto-detect
            
        Returns:
            Dict with status
        """
        yaml_file = os.path.join(self.build_dir, f"{controller_name.lower().replace(' ', '-')}.yaml")
        
        if not os.path.exists(yaml_file):
            return {'success': False, 'error': f'Config file not found: {yaml_file}'}
        
        try:
            logger.info(f"⚡ Flashing firmware to {controller_name} on {port}...")
            
            # Build command
            cmd = ['esphome', 'run', yaml_file]
            if port != 'auto':
                cmd.extend(['--device', port])
            
            # Run ESPHome upload command
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600
            )
            
            if result.returncode == 0:
                logger.info(f"✅ Flashing successful!")
                return {
                    'success': True,
                    'output': result.stdout
                }
            else:
                logger.error(f"❌ Flashing failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'output': result.stdout
                }
                
        except subprocess.TimeoutExpired:
            logger.error("⏱️ Flashing timeout")
            return {'success': False, 'error': 'Flashing timeout (10 minutes)'}
        except Exception as e:
            logger.error(f"❌ Flashing error: {e}")
            return {'success': False, 'error': str(e)}
    
    def compile_and_flash(self, controller_name: str, port: str = 'auto') -> Dict:
        """Compile and flash in one operation"""
        logger.info(f"🚀 Starting compile and flash for {controller_name}...")
        
        # Compile
        compile_result = self.compile_firmware(controller_name)
        if not compile_result['success']:
            return compile_result
        
        # Flash
        flash_result = self.flash_firmware(controller_name, port)
        return flash_result
    
    def list_serial_ports(self) -> list:
        """List available serial ports for flashing"""
        try:
            # Look for common ESP32 serial ports
            ports = []
            
            # Linux/Home Assistant OS
            for device in ['/dev/ttyUSB0', '/dev/ttyUSB1', '/dev/ttyACM0', '/dev/ttyACM1']:
                if os.path.exists(device):
                    ports.append(device)
            
            return ports
        except Exception as e:
            logger.error(f"Error listing serial ports: {e}")
            return []
    
    def _find_firmware_binary(self, controller_name: str) -> Optional[str]:
        """Find the compiled firmware binary"""
        # ESPHome typically puts binaries in .esphome/build/<name>/
        build_name = controller_name.lower().replace(' ', '-')
        possible_paths = [
            f"{self.build_dir}/.esphome/build/{build_name}/.pioenvs/{build_name}/firmware.bin",
            f"{self.build_dir}/.esphome/build/{build_name}/firmware.bin",
        ]
        
        for path in possible_paths:
            if os.path.exists(path):
                return path
        
        return None
    
    def update_secrets(self, secrets: Dict) -> bool:
        """Update secrets.yaml file
        
        Args:
            secrets: Dict of secret key-value pairs
            
        Returns:
            bool: Success status
        """
        try:
            import yaml
            
            # Load existing secrets
            existing = {}
            if os.path.exists(self.secrets_file):
                with open(self.secrets_file, 'r') as f:
                    existing = yaml.safe_load(f) or {}
            
            # Merge with new secrets
            existing.update(secrets)
            
            # Save back
            with open(self.secrets_file, 'w') as f:
                yaml.dump(existing, f, default_flow_style=False)
            
            logger.info(f"✅ Updated secrets: {list(secrets.keys())}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to update secrets: {e}")
            return False
    
    def generate_api_key(self) -> str:
        """Generate a random API encryption key for ESPHome"""
        import secrets
        import base64
        
        # Generate 32 random bytes and encode as base64
        key_bytes = secrets.token_bytes(32)
        key = base64.b64encode(key_bytes).decode('ascii')
        return key
