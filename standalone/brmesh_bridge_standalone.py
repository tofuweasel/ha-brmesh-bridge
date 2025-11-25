#!/usr/bin/env python3
"""
BRMesh Bridge Standalone - Desktop application version
No Home Assistant required!
"""
import os
import sys
import json
import logging
import webbrowser
import threading
from pathlib import Path

# Add parent directory to path to import bridge modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'brmesh-bridge', 'rootfs', 'app'))

from brmesh_bridge import BRMeshBridge
from web_ui import WebUI

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StandaloneBridge:
    """Standalone version of BRMesh Bridge"""
    
    def __init__(self):
        self.config_dir = self._get_config_dir()
        self.config_file = os.path.join(self.config_dir, 'config.json')
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, exist_ok=True)
        
        # Load or create config
        self.config = self._load_config()
        
        # Initialize bridge with standalone config
        self.bridge = BRMeshBridge(self.config)
        
        # Initialize web UI
        self.web_ui = WebUI(self.bridge)
    
    def _get_config_dir(self):
        """Get platform-specific config directory"""
        if sys.platform == 'win32':
            # Windows: %APPDATA%\BRMeshBridge
            return os.path.join(os.environ.get('APPDATA', ''), 'BRMeshBridge')
        elif sys.platform == 'darwin':
            # macOS: ~/Library/Application Support/BRMeshBridge
            return os.path.join(Path.home(), 'Library', 'Application Support', 'BRMeshBridge')
        else:
            # Linux: ~/.config/brmesh-bridge
            return os.path.join(Path.home(), '.config', 'brmesh-bridge')
    
    def _load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_file):
            try:
                with open(self.config_file, 'r') as f:
                    config = json.load(f)
                logger.info(f"Loaded config from {self.config_file}")
                return config
            except Exception as e:
                logger.error(f"Failed to load config: {e}")
        
        # Return default config
        return self._default_config()
    
    def _default_config(self):
        """Create default configuration"""
        return {
            'mesh_key': '',
            'mqtt_host': 'localhost',
            'mqtt_port': 1883,
            'mqtt_user': '',
            'mqtt_password': '',
            'use_addon_mqtt': False,  # No HA MQTT in standalone
            'lights': [],
            'controllers': [],
            'scenes': [],
            'map_enabled': True,
            'map_latitude': 0,
            'map_longitude': 0,
            'map_zoom': 18,
            'enable_ble_discovery': True,
            'generate_esphome_configs': True,
            'enable_nspanel_ui': False
        }
    
    def save_config(self):
        """Save configuration to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.config, f, indent=2)
            logger.info(f"Saved config to {self.config_file}")
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    def run(self):
        """Run the standalone application"""
        print("=" * 80)
        print("🌟 BRMesh Bridge Standalone 🌟")
        print("=" * 80)
        print(f"📂 Config directory: {self.config_dir}")
        print(f"🌐 Web UI: http://localhost:8099")
        print(f"💡 Lights configured: {len(self.config.get('lights', []))}")
        print(f"🎮 Controllers: {len(self.config.get('controllers', []))}")
        print("=" * 80)
        print()
        
        if not self.config.get('mesh_key'):
            print("⚠️  WARNING: No mesh key configured!")
            print("   Open the web UI and go to Settings to configure your mesh key.")
            print()
        
        # Open web browser after a short delay
        def open_browser():
            import time
            time.sleep(2)
            webbrowser.open('http://localhost:8099')
        
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Run the bridge
        try:
            import asyncio
            asyncio.run(self.bridge.run())
        except KeyboardInterrupt:
            logger.info("Shutting down...")
            self.save_config()
            print("\n👋 Goodbye!")

def main():
    """Main entry point"""
    try:
        app = StandaloneBridge()
        app.run()
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        input("Press Enter to exit...")
        sys.exit(1)

if __name__ == '__main__':
    main()
