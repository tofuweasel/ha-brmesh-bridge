#!/usr/bin/env python3
"""
BRMesh Bridge Web UI - Map view, light management, effects control
"""
from flask import Flask, render_template, jsonify, request, send_from_directory, Response
from flask_cors import CORS
from werkzeug.middleware.proxy_fix import ProxyFix
import json
import logging
import os
import requests
from PIL import Image
from io import BytesIO
from esphome_generator import ESPHomeConfigGenerator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='/app/static', template_folder='/app/templates')
# Handle Home Assistant Ingress reverse proxy headers
app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)
CORS(app)

class WebUI:
    def __init__(self, bridge):
        self.bridge = bridge
        self.setup_routes()
    
    def _update_ha_secrets(self, wifi_ssid=None, wifi_password=None, network_id=None):
        """Update Home Assistant's secrets.yaml with WiFi credentials
        
        If network_id is provided, uses that specific network from the list.
        Otherwise, updates the default wifi_ssid/wifi_password for new controllers.
        """
        import yaml
        
        secrets_path = '/config/secrets.yaml'
        secrets = {}
        
        # Load existing secrets if file exists
        if os.path.exists(secrets_path):
            try:
                with open(secrets_path, 'r') as f:
                    secrets = yaml.safe_load(f) or {}
            except Exception as e:
                logger.warning(f"Could not read existing secrets.yaml: {e}")
        
        # If network_id provided, get credentials from that network
        if network_id is not None:
            wifi_ssid = secrets.get(f'wifi_network_{network_id}_ssid')
            wifi_password = secrets.get(f'wifi_network_{network_id}_password')
            if not wifi_ssid or not wifi_password:
                raise ValueError(f"WiFi network {network_id} not found in secrets.yaml")
        
        # Validate we have credentials
        if not wifi_ssid or not wifi_password:
            raise ValueError("WiFi SSID and password are required")
        
        # Update default WiFi credentials (used by ESPHome configs)
        secrets['wifi_ssid'] = wifi_ssid
        secrets['wifi_password'] = wifi_password
        
        # Add other common secrets if they don't exist
        if 'gateway' not in secrets:
            secrets['gateway'] = '192.168.1.1'
        if 'subnet' not in secrets:
            secrets['subnet'] = '255.255.255.0'
        
        # Save back to file
        with open(secrets_path, 'w') as f:
            yaml.dump(secrets, f, default_flow_style=False, sort_keys=False)
        
        logger.info(f"✅ Updated secrets.yaml with WiFi SSID: {wifi_ssid}")
    
    def setup_routes(self):
        """Setup Flask routes"""
        
        @app.route('/')
        def index():
            return render_template('index.html')
        
        @app.route('/api/config')
        def get_config():
            """Get current configuration"""
            try:
                # Return the bridge's runtime config (includes auto-detected location)
                return jsonify(self.bridge.config)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/lights')
        def get_lights():
            """Get all lights with status"""
            lights = []
            for light_id, light in self.bridge.lights.items():
                lights.append({
                    'id': light_id,
                    'name': light['name'],
                    'state': light['state'],
                    'location': light.get('location', {'x': None, 'y': None}),
                    'signal_strength': light.get('signal_strength', {})
                })
            return jsonify(lights)
        
        @app.route('/api/lights/<int:light_id>', methods=['POST'])
        def control_light(light_id):
            """Control a specific light"""
            try:
                data = request.json
                state = data.get('state', True)
                brightness = data.get('brightness', 255)
                rgb = tuple(data.get('rgb', [255, 255, 255]))
                
                self.bridge.set_light_color(light_id, rgb, brightness, state)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/lights/<int:light_id>/location', methods=['POST'])
        def set_light_location(light_id):
            """Set light location on map"""
            try:
                data = request.json
                x = data.get('x')
                y = data.get('y')
                
                if light_id in self.bridge.lights:
                    self.bridge.lights[light_id]['location'] = {'x': x, 'y': y}
                    self.bridge.save_config()
                    return jsonify({'success': True})
                return jsonify({'error': 'Light not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/controllers')
        def get_controllers():
            """Get all ESP32 controllers"""
            return jsonify(self.bridge.controllers)
        
        @app.route('/api/controllers/<controller_name>/signal', methods=['GET'])
        def get_controller_signal(controller_name):
            """Get signal strength from controller to all lights"""
            # This would query the ESP32 for RSSI values
            return jsonify(self.bridge.get_controller_signal_map(controller_name))
        
        @app.route('/api/controllers/<controller_id>/location', methods=['PUT'])
        def update_controller_location(controller_id):
            """Update controller location on map"""
            try:
                data = request.json
                x = data.get('x')
                y = data.get('y')
                
                if x is None or y is None:
                    return jsonify({'success': False, 'error': 'x and y coordinates required'}), 400
                
                # Update controller location in config
                if 'controllers' not in self.bridge.config:
                    self.bridge.config['controllers'] = []
                
                for controller in self.bridge.config['controllers']:
                    if controller.get('id') == controller_id or controller.get('name') == controller_id:
                        controller['location'] = {'x': x, 'y': y}
                        self.bridge.save_config()
                        return jsonify({'success': True})
                
                return jsonify({'success': False, 'error': 'Controller not found'}), 404
                
            except Exception as e:
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @app.route('/api/effects', methods=['GET'])
        def list_effects():
            """List available effects"""
            effects = [
                {'name': 'rainbow', 'params': ['speed', 'brightness']},
                {'name': 'color_loop', 'params': ['colors', 'interval']},
                {'name': 'twinkle', 'params': ['color', 'speed']},
                {'name': 'fire', 'params': ['intensity']},
                {'name': 'christmas', 'params': ['interval']},
                {'name': 'halloween', 'params': ['interval']},
                {'name': 'strobe', 'params': ['color', 'frequency']},
                {'name': 'breathe', 'params': ['color', 'speed']},
            ]
            return jsonify(effects)
        
        @app.route('/api/effects/<effect_name>', methods=['POST'])
        def start_effect(effect_name):
            """Start an effect on selected lights"""
            try:
                data = request.json
                light_ids = data.get('light_ids', [])
                params = data.get('params', {})
                
                self.bridge.effects.start_effect(light_ids, effect_name, **params)
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/effects/stop', methods=['POST'])
        def stop_effects():
            """Stop all effects"""
            try:
                data = request.json
                effect_id = data.get('effect_id')
                
                if effect_id:
                    self.bridge.effects.stop_effect(effect_id)
                else:
                    # Stop all
                    for effect_id in list(self.bridge.effects.running_effects.keys()):
                        self.bridge.effects.stop_effect(effect_id)
                
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/scenes', methods=['GET'])
        def list_scenes():
            """List saved scenes"""
            try:
                with open('/data/options.json', 'r') as f:
                    config = json.load(f)
                return jsonify(config.get('scenes', []))
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/scenes', methods=['POST'])
        def create_scene():
            """Create a new scene"""
            try:
                scene_data = request.json
                # Save scene to config
                self.bridge.config.setdefault('scenes', []).append(scene_data)
                self.bridge.save_config()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/scenes/<scene_name>', methods=['POST'])
        def apply_scene(scene_name):
            """Apply a saved scene"""
            try:
                scenes = self.bridge.config.get('scenes', [])
                scene = next((s for s in scenes if s['name'] == scene_name), None)
                
                if scene:
                    self.bridge.effects.apply_scene(scene)
                    return jsonify({'success': True})
                return jsonify({'error': 'Scene not found'}), 404
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/controllers', methods=['POST'])
        def add_controller():
            """Add a new ESP32 controller"""
            try:
                controller_data = request.json
                
                # Log controller data with masked secrets
                safe_data = controller_data.copy()
                if 'wifi_password' in safe_data:
                    safe_data['wifi_password'] = '***MASKED***'
                logger.info(f"📡 Received controller data: {safe_data}")
                
                # Auto-generate name if not provided
                if not controller_data.get('name'):
                    existing_controllers = self.bridge.config.get('controllers', [])
                    base_name = 'brmesh_bridge'
                    
                    # Check if base name exists
                    existing_names = [c.get('name', '').lower() for c in existing_controllers]
                    if base_name not in existing_names:
                        controller_data['name'] = base_name
                    else:
                        # Find next available number
                        counter = 1
                        while f"{base_name}_{counter}" in existing_names:
                            counter += 1
                        controller_data['name'] = f"{base_name}_{counter}"
                    
                    logger.info(f"🏷️  Auto-generated controller name: {controller_data['name']}")
                
                # Generate unique ID
                controller_id = len(self.bridge.config.get('controllers', [])) + 1
                controller_data['id'] = controller_id
                
                # Handle WiFi secrets for new controllers
                if controller_data.get('generate_esphome'):
                    network_id = controller_data.pop('network_id', None)
                    wifi_ssid = controller_data.pop('wifi_ssid', None)
                    wifi_password = controller_data.pop('wifi_password', None)
                    
                    # Update Home Assistant's secrets.yaml
                    try:
                        if network_id is not None:
                            # Using pre-configured network
                            self._update_ha_secrets(network_id=network_id)
                            logger.info(f"🔐 Using WiFi network #{network_id} from /config/secrets.yaml")
                        elif wifi_ssid and wifi_password:
                            # Using new WiFi credentials
                            self._update_ha_secrets(wifi_ssid, wifi_password)
                            logger.info(f"🔐 Updated WiFi credentials in /config/secrets.yaml")
                        else:
                            logger.error("No WiFi credentials provided")
                            return jsonify({'error': 'WiFi credentials are required for new controllers'}), 400
                    except Exception as e:
                        logger.error(f"Failed to update secrets: {e}")
                        return jsonify({'error': f'Failed to save WiFi credentials: {e}'}), 500
                
                # Add to config
                self.bridge.config.setdefault('controllers', []).append(controller_data)
                self.bridge.save_config()
                
                # Generate ESPHome config if requested
                esphome_path = None
                if controller_data.get('generate_esphome') and self.bridge.esphome_generator:
                    # All controllers get all lights in a mesh network
                    yaml_config = self.bridge.esphome_generator.generate_controller_config(controller_data)
                    
                    # Save to file
                    controller_name = controller_data['name'].lower().replace(' ', '-')
                    filename = f"{controller_name}.yaml"
                    filepath = os.path.join('/config/esphome', filename)
                    
                    try:
                        os.makedirs('/config/esphome', exist_ok=True)
                        with open(filepath, 'w') as f:
                            f.write(yaml_config)
                        esphome_path = filepath
                        logger.info(f"📝 Generated ESPHome config: {filepath}")
                    except Exception as e:
                        logger.error(f"Failed to write ESPHome config: {e}")
                
                logger.info(f"✅ Controller '{controller_data['name']}' added successfully with ID: {controller_id}")
                return jsonify({
                    'success': True, 
                    'id': controller_id, 
                    'name': controller_data['name'],
                    'esphome_path': esphome_path
                })
            except Exception as e:
                logger.error(f"❌ Error adding controller: {str(e)}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/map/satellite')
        def get_satellite_map():
            """Get satellite imagery for the property"""
            try:
                with open('/data/options.json', 'r') as f:
                    config = json.load(f)
                
                lat = config.get('map_latitude', 0)
                lon = config.get('map_longitude', 0)
                zoom = config.get('map_zoom', 19)
                
                # Use OpenStreetMap or Google Maps Static API
                # For now, return a placeholder
                return jsonify({
                    'url': f'https://maps.googleapis.com/maps/api/staticmap?center={lat},{lon}&zoom={zoom}&size=800x800&maptype=satellite',
                    'center': {'lat': lat, 'lon': lon},
                    'zoom': zoom
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/scan', methods=['POST'])
        def scan_for_lights():
            """Scan BRMesh network for new lights"""
            try:
                logger.info("🔍 Scan request received")
                
                # Run BLE discovery if available
                if self.bridge.ble_discovery:
                    logger.info("📡 Starting BLE discovery (30 second scan)...")
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    new_lights = loop.run_until_complete(
                        self.bridge.ble_discovery.auto_discover_and_register(duration=30)
                    )
                    loop.close()
                    logger.info(f"✅ Scan complete. Found {len(new_lights)} new lights: {new_lights}")
                    return jsonify({'lights': new_lights, 'count': len(new_lights)})
                else:
                    logger.warning("⚠️ BLE discovery not enabled in bridge")
                    return jsonify({'error': 'BLE discovery not enabled. Check bluetooth permissions and enable_ble_discovery setting.'}), 400
            except Exception as e:
                logger.error(f"❌ Scan error: {str(e)}", exc_info=True)
                # Provide helpful error message for common Bluetooth issues
                error_msg = str(e)
                if 'No such file or directory' in error_msg or 'Errno 2' in error_msg:
                    error_msg = 'Bluetooth adapter not accessible. Make sure the add-on has bluetooth: true in config and your system has Bluetooth hardware.'
                return jsonify({'error': error_msg}), 500
        
        @app.route('/api/import/app', methods=['POST'])
        def import_from_app():
            """Import configuration from BRMesh app"""
            try:
                if not self.bridge.app_importer:
                    return jsonify({'error': 'App importer not available'}), 400
                
                # Sync from ADB
                count = self.bridge.app_importer.sync_device_names_from_app()
                return jsonify({'success': True, 'devices_updated': count})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/esphome/generate', methods=['POST'])
        def generate_esphome_configs():
            """Generate ESPHome YAML configurations"""
            try:
                if not self.bridge.esphome_generator:
                    self.bridge.esphome_generator = ESPHomeConfigGenerator(self.bridge)
                
                configs = self.bridge.esphome_generator.generate_all_configs()
                return jsonify({
                    'success': True,
                    'configs': configs,
                    'count': len(configs)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/esphome/download/<controller_name>')
        def download_esphome_config(controller_name):
            """Download ESPHome YAML for a specific controller"""
            try:
                if not self.bridge.esphome_generator:
                    return jsonify({'error': 'ESPHome generator not available'}), 400
                
                controller = next((c for c in self.bridge.controllers if c['name'] == controller_name), None)
                if not controller:
                    return jsonify({'error': 'Controller not found'}), 404
                
                # Find assigned lights
                assigned_lights = [
                    light_id for light_id, light in self.bridge.lights.items()
                    if light.get('preferred_controller') == controller_name
                ]
                
                yaml_config = self.bridge.esphome_generator.generate_controller_config(controller, assigned_lights)
                
                return Response(
                    yaml_config,
                    mimetype='text/yaml',
                    headers={'Content-Disposition': f'attachment; filename={controller_name}.yaml'}
                )
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/esphome/build/<controller_name>', methods=['POST'])
        def build_firmware(controller_name):
            """Compile firmware for a controller"""
            try:
                if not hasattr(self.bridge, 'esphome_builder'):
                    return jsonify({'error': 'ESPHome builder not available'}), 400
                
                logger.info(f"🔨 Starting firmware build for {controller_name}")
                result = self.bridge.esphome_builder.compile_firmware(controller_name)
                
                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify(result), 500
            except Exception as e:
                logger.error(f"Build error: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/esphome/flash/<controller_name>', methods=['POST'])
        def flash_firmware(controller_name):
            """Flash firmware to ESP32"""
            try:
                if not hasattr(self.bridge, 'esphome_builder'):
                    return jsonify({'error': 'ESPHome builder not available'}), 400
                
                data = request.json or {}
                port = data.get('port', 'auto')
                
                logger.info(f"⚡ Starting firmware flash for {controller_name} on {port}")
                result = self.bridge.esphome_builder.flash_firmware(controller_name, port)
                
                if result['success']:
                    return jsonify(result)
                else:
                    return jsonify(result), 500
            except Exception as e:
                logger.error(f"Flash error: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/esphome/ports', methods=['GET'])
        def get_serial_ports():
            """List available serial ports"""
            try:
                if not hasattr(self.bridge, 'esphome_builder'):
                    return jsonify({'error': 'ESPHome builder not available'}), 400
                
                ports = self.bridge.esphome_builder.list_serial_ports()
                return jsonify({'ports': ports})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/nspanel/refresh', methods=['POST'])
        def refresh_nspanel():
            """Refresh NSPanel display"""
            try:
                if not self.bridge.nspanel_ui:
                    return jsonify({'error': 'NSPanel UI not enabled'}), 400
                
                self.bridge.nspanel_ui.refresh_nspanel_display()
                return jsonify({'success': True})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/settings', methods=['GET'])
        def get_settings():
            """Get all configuration settings"""
            try:
                settings = {
                    'mesh_key': self.bridge.mesh_key,
                    'use_addon_mqtt': self.bridge.config.get('use_addon_mqtt', True),
                    'mqtt_host': self.bridge.config.get('mqtt_host', ''),
                    'mqtt_port': self.bridge.config.get('mqtt_port', 1883),
                    'mqtt_user': self.bridge.config.get('mqtt_user', ''),
                    'mqtt_password': '',  # Don't expose password
                    'map_enabled': self.bridge.config.get('map_enabled', True),
                    'latitude': self.bridge.config.get('latitude', 0),
                    'longitude': self.bridge.config.get('longitude', 0),
                    'zoom': self.bridge.config.get('zoom', 18),
                    'discovery_enabled': self.bridge.config.get('discovery_enabled', True),
                    'generate_esphome': self.bridge.config.get('generate_esphome', True),
                    'enable_ble': self.bridge.config.get('enable_ble', True),
                    'enable_nspanel': self.bridge.config.get('enable_nspanel', False),
                    'nspanel_entity_id': self.bridge.config.get('nspanel_entity_id', ''),
                    'app_config_path': self.bridge.config.get('app_config_path', '/share/brmesh_export.json')
                }
                return jsonify(settings)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/settings', methods=['POST'])
        def update_settings():
            """Update configuration settings"""
            try:
                settings = request.json
                
                # Update add-on options file
                options_path = '/data/options.json'
                with open(options_path, 'r') as f:
                    options = json.load(f)
                
                # Update all settings
                mesh_key = settings.get('mesh_key', options.get('mesh_key', ''))
                options['mesh_key'] = mesh_key
                options['use_addon_mqtt'] = settings.get('use_addon_mqtt', True)
                
                if not options['use_addon_mqtt']:
                    options['mqtt_host'] = settings.get('mqtt_host', '')
                    options['mqtt_port'] = settings.get('mqtt_port', 1883)
                    options['mqtt_user'] = settings.get('mqtt_user', '')
                    if settings.get('mqtt_password'):  # Only update if provided
                        options['mqtt_password'] = settings.get('mqtt_password')
                
                options['map_enabled'] = settings.get('map_enabled', True)
                options['latitude'] = settings.get('latitude', 0)
                options['longitude'] = settings.get('longitude', 0)
                options['zoom'] = settings.get('zoom', 18)
                options['discovery_enabled'] = settings.get('discovery_enabled', True)
                options['generate_esphome'] = settings.get('generate_esphome', True)
                options['enable_ble'] = settings.get('enable_ble', True)
                options['enable_nspanel'] = settings.get('enable_nspanel', False)
                options['nspanel_entity_id'] = settings.get('nspanel_entity_id', '')
                options['app_config_path'] = settings.get('app_config_path', '/share/brmesh_export.json')
                
                # Save updated options
                with open(options_path, 'w') as f:
                    json.dump(options, f, indent=2)
                
                # Update runtime config immediately (so it persists when save_config() is called)
                self.bridge.config.update(options)
                self.bridge.mesh_key = mesh_key
                logger.info(f"🔑 Updated mesh key: {self.bridge.mesh_key}")
                
                # Also save mesh_key to secrets.yaml for ESPHome configs
                if mesh_key:
                    try:
                        import yaml
                        secrets_path = '/config/secrets.yaml'
                        secrets = {}
                        
                        # Load existing secrets if file exists
                        if os.path.exists(secrets_path):
                            try:
                                with open(secrets_path, 'r') as f:
                                    secrets = yaml.safe_load(f) or {}
                            except Exception as e:
                                logger.warning(f"Could not read existing secrets.yaml: {e}")
                        
                        # Update mesh_key in secrets
                        secrets['mesh_key'] = mesh_key
                        
                        # Save back to file
                        with open(secrets_path, 'w') as f:
                            yaml.dump(secrets, f, default_flow_style=False, sort_keys=False)
                        
                        logger.info(f"✅ Saved mesh key to /config/secrets.yaml")
                    except Exception as e:
                        logger.error(f"Failed to save mesh key to secrets.yaml: {e}")
                
                # Save to ensure mesh_key is persisted in the lights/controllers config
                self.bridge.save_config()
                
                return jsonify({'success': True, 'message': 'Settings saved. Please restart the add-on.'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/settings/reset', methods=['POST'])
        def reset_settings():
            """Reset settings to defaults"""
            try:
                default_settings = {
                    'mesh_key': '',
                    'use_addon_mqtt': True,
                    'map_enabled': True,
                    'latitude': 0,
                    'longitude': 0,
                    'zoom': 18,
                    'discovery_enabled': True,
                    'generate_esphome': True,
                    'enable_ble': True,
                    'enable_nspanel': False,
                    'controllers': [],
                    'lights': {},
                    'scenes': []
                }
                
                options_path = '/data/options.json'
                with open(options_path, 'w') as f:
                    json.dump(default_settings, f, indent=2)
                
                return jsonify({'success': True, 'message': 'Settings reset to defaults. Restart the add-on.'})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/wifi-networks', methods=['GET'])
        def get_wifi_networks():
            """Get list of configured WiFi networks (SSIDs only, not passwords)"""
            try:
                import yaml
                secrets_path = '/config/secrets.yaml'
                
                if not os.path.exists(secrets_path):
                    return jsonify({'networks': []})
                
                with open(secrets_path, 'r') as f:
                    secrets = yaml.safe_load(f) or {}
                
                # Get all wifi network SSIDs (stored as wifi_network_0, wifi_network_1, etc.)
                networks = []
                i = 0
                while f'wifi_network_{i}_ssid' in secrets:
                    networks.append({
                        'id': i,
                        'ssid': secrets[f'wifi_network_{i}_ssid']
                    })
                    i += 1
                
                # Also check for legacy wifi_ssid
                if 'wifi_ssid' in secrets and not networks:
                    networks.append({
                        'id': -1,  # Legacy entry
                        'ssid': secrets['wifi_ssid']
                    })
                
                return jsonify({'networks': networks})
            except Exception as e:
                logger.error(f"Failed to get WiFi networks: {e}")
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/wifi-networks', methods=['POST'])
        def add_wifi_network():
            """Add a new WiFi network"""
            try:
                import yaml
                data = request.json
                ssid = data.get('ssid')
                password = data.get('password')
                
                if not ssid or not password:
                    return jsonify({'error': 'SSID and password required'}), 400
                
                secrets_path = '/config/secrets.yaml'
                secrets = {}
                
                if os.path.exists(secrets_path):
                    with open(secrets_path, 'r') as f:
                        secrets = yaml.safe_load(f) or {}
                
                # Find next available ID
                i = 0
                while f'wifi_network_{i}_ssid' in secrets:
                    i += 1
                
                # Add new network
                secrets[f'wifi_network_{i}_ssid'] = ssid
                secrets[f'wifi_network_{i}_password'] = password
                
                # Save
                with open(secrets_path, 'w') as f:
                    yaml.dump(secrets, f, default_flow_style=False, sort_keys=False)
                
                logger.info(f"✅ Added WiFi network: {ssid}")
                return jsonify({'success': True, 'id': i, 'ssid': ssid})
            except Exception as e:
                logger.error(f"Failed to add WiFi network: {e}")
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/wifi-networks/<int:network_id>', methods=['DELETE'])
        def delete_wifi_network(network_id):
            """Delete a WiFi network and reindex remaining networks"""
            try:
                import yaml
                secrets_path = '/config/secrets.yaml'
                
                if not os.path.exists(secrets_path):
                    return jsonify({'error': 'No WiFi networks configured'}), 404
                
                with open(secrets_path, 'r') as f:
                    secrets = yaml.safe_load(f) or {}
                
                # Check if network exists
                ssid_key = f'wifi_network_{network_id}_ssid'
                pass_key = f'wifi_network_{network_id}_password'
                
                if ssid_key not in secrets:
                    return jsonify({'error': 'Network not found'}), 404
                
                ssid = secrets[ssid_key]
                
                # Collect all existing networks
                networks = []
                i = 0
                while f'wifi_network_{i}_ssid' in secrets:
                    if i != network_id:  # Skip the one being deleted
                        networks.append({
                            'ssid': secrets[f'wifi_network_{i}_ssid'],
                            'password': secrets[f'wifi_network_{i}_password']
                        })
                    # Remove old keys
                    secrets.pop(f'wifi_network_{i}_ssid', None)
                    secrets.pop(f'wifi_network_{i}_password', None)
                    i += 1
                
                # Re-add networks with sequential IDs starting from 0
                for idx, network in enumerate(networks):
                    secrets[f'wifi_network_{idx}_ssid'] = network['ssid']
                    secrets[f'wifi_network_{idx}_password'] = network['password']
                
                # Save
                with open(secrets_path, 'w') as f:
                    yaml.dump(secrets, f, default_flow_style=False, sort_keys=False)
                
                logger.info(f"🗑️  Deleted WiFi network: {ssid} (reindexed {len(networks)} remaining networks)")
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Failed to delete WiFi network: {e}")
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/settings/import-app', methods=['POST'])
        def import_from_app_settings():
            """Import configuration from BRMesh app (via settings)"""
            try:
                if not self.bridge.app_importer:
                    return jsonify({'error': 'App importer not available'}), 400
                
                app_config_path = self.bridge.config.get('app_config_path', '/share/brmesh_export.json')
                
                # Try JSON import first if file exists
                if os.path.exists(app_config_path):
                    result = self.bridge.app_importer.import_from_json_export(app_config_path)
                    if result:
                        return jsonify({
                            'success': True,
                            'lights_imported': len(result.get('lights', [])),
                            'mesh_key': result.get('mesh_key', ''),
                            'method': 'json'
                        })
                
                # Fall back to ADB logcat
                count = self.bridge.app_importer.sync_device_names_from_app()
                return jsonify({
                    'success': True,
                    'lights_imported': count,
                    'method': 'adb'
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/settings/export')
        def export_settings():
            """Export complete configuration as JSON"""
            try:
                config_data = {
                    'mesh_key': self.bridge.mesh_key,
                    'controllers': self.bridge.controllers,
                    'lights': self.bridge.lights,
                    'scenes': self.bridge.config.get('scenes', []),
                    'settings': {
                        'mqtt_host': self.bridge.config.get('mqtt_host', ''),
                        'mqtt_port': self.bridge.config.get('mqtt_port', 1883),
                        'latitude': self.bridge.config.get('latitude', 0),
                        'longitude': self.bridge.config.get('longitude', 0),
                        'zoom': self.bridge.config.get('zoom', 18)
                    }
                }
                
                return Response(
                    json.dumps(config_data, indent=2),
                    mimetype='application/json',
                    headers={'Content-Disposition': 'attachment; filename=brmesh_config.json'}
                )
            except Exception as e:
                return jsonify({'error': str(e)}), 500
    
    def run(self, host='0.0.0.0', port=8099):
        """Run the web UI"""
        app.run(host=host, port=port, debug=False)
