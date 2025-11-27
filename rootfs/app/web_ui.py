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
from brmesh_pairing import create_pairing_response
from brmesh_control import create_control_command, decode_control_command

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
    
    def _get_yaml_handler(self):
        """Get ruamel.yaml instance configured to preserve comments"""
        from ruamel.yaml import YAML
        yaml = YAML()
        yaml.preserve_quotes = True
        yaml.default_flow_style = False
        return yaml
    
    def _update_ha_secrets(self, wifi_ssid=None, wifi_password=None, network_id=None):
        """Update Home Assistant's secrets.yaml with WiFi credentials
        
        If network_id is provided, uses that specific network from the list.
        Otherwise, updates the default wifi_ssid/wifi_password for new controllers.
        Uses ruamel.yaml to preserve comments and formatting.
        """
        secrets_path = '/config/secrets.yaml'
        yaml = self._get_yaml_handler()
        
        secrets = {}
        
        # Load existing secrets if file exists
        if os.path.exists(secrets_path):
            try:
                with open(secrets_path, 'r') as f:
                    secrets = yaml.load(f) or {}
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
        # Use PlainScalarString to avoid quotes being added
        from ruamel.yaml.scalarstring import PlainScalarString
        secrets['wifi_ssid'] = PlainScalarString(str(wifi_ssid))
        secrets['wifi_password'] = PlainScalarString(str(wifi_password))
        
        # Add other common secrets if they don't exist (but preserve existing values)
        if 'gateway' not in secrets:
            secrets['gateway'] = '192.168.1.1'
        if 'subnet' not in secrets:
            secrets['subnet'] = '255.255.255.0'
        # Don't overwrite api_encryption_key or ota_password - they should be preserved
        
        # Save back to file (preserving comments and formatting)
        with open(secrets_path, 'w') as f:
            yaml.dump(secrets, f)
        
        # Log the encryption key to verify it wasn't corrupted
        api_key = secrets.get('api_encryption_key', '')
        logger.info(f"✅ Updated secrets.yaml with WiFi SSID: {wifi_ssid}")
        if api_key:
            logger.info(f"🔑 Preserved api_encryption_key: {api_key[:20]}... (length: {len(api_key)})")
    
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
            """Get all ESP32 controllers with enhanced status info"""
            controllers_with_status = []
            for controller in self.bridge.controllers:
                # Add computed fields for web UI display
                controller_info = controller.copy()
                controller_info['online'] = controller.get('status') == 'online'
                controller_info['config_status'] = 'configured' if controller.get('name') else 'no_config'
                controllers_with_status.append(controller_info)
            return jsonify(controllers_with_status)
        
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
        
        @app.route('/api/controllers/<int:controller_id>', methods=['PUT'])
        def update_controller(controller_id):
            """Update controller details"""
            try:
                if 'controllers' not in self.bridge.config:
                    return jsonify({'success': False, 'error': 'No controllers configured'}), 404
                
                data = request.json
                controllers = self.bridge.config['controllers']
                controller = next((c for c in controllers if c.get('id') == controller_id), None)
                
                if not controller:
                    return jsonify({'success': False, 'error': 'Controller not found'}), 404
                
                # Update fields
                if 'name' in data:
                    controller['name'] = data['name']
                if 'ip' in data:
                    controller['ip'] = data['ip']
                if 'mac' in data:
                    controller['mac'] = data['mac']
                
                self.bridge.save_config()
                
                logger.info(f"✏️  Updated controller: {controller.get('name')} (ID: {controller_id})")
                return jsonify({'success': True, 'controller': controller})
                
            except Exception as e:
                logger.error(f"Failed to update controller: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @app.route('/api/controllers/<int:controller_id>', methods=['DELETE'])
        def delete_controller(controller_id):
            """Delete a controller"""
            try:
                if 'controllers' not in self.bridge.config:
                    return jsonify({'success': False, 'error': 'No controllers configured'}), 404
                
                # Find and remove controller
                controllers = self.bridge.config['controllers']
                controller = next((c for c in controllers if c.get('id') == controller_id), None)
                
                if not controller:
                    return jsonify({'success': False, 'error': 'Controller not found'}), 404
                
                controllers.remove(controller)
                self.bridge.save_config()
                
                logger.info(f"🗑️  Deleted controller: {controller.get('name')} (ID: {controller_id})")
                return jsonify({'success': True})
                
            except Exception as e:
                logger.error(f"Failed to delete controller: {e}")
                return jsonify({'success': False, 'error': str(e)}), 500
        
        @app.route('/api/esphome/build-status/<controller_name>')
        def get_build_status(controller_name):
            """Check if firmware has been built for a controller"""
            try:
                # Check for .bin file in ESPHome build directory
                build_path = f'/config/esphome/.esphome/build/{controller_name}/.pioenvs/{controller_name}/firmware.bin'
                built = os.path.exists(build_path)
                
                return jsonify({
                    'built': built,
                    'path': build_path if built else None
                })
            except Exception as e:
                return jsonify({'built': False, 'error': str(e)}), 500
        
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
                    base_name = 'esp-ble-bridge'
                    
                    # Check if base name exists
                    existing_names = [c.get('name', '').lower() for c in existing_controllers]
                    if base_name not in existing_names:
                        controller_data['name'] = base_name
                    else:
                        # Find next available number
                        counter = 1
                        while f"{base_name}-{counter}" in existing_names:
                            counter += 1
                        controller_data['name'] = f"{base_name}-{counter}"
                    
                    logger.info(f"🏷️  Auto-generated controller name: {controller_data['name']}")
                
                # Generate unique ID
                controller_id = len(self.bridge.config.get('controllers', [])) + 1
                controller_data['id'] = controller_id
                
                # Handle WiFi secrets for new controllers
                if controller_data.get('generate_esphome'):
                    # First ensure secrets.yaml has valid encryption keys
                    if self.bridge.esphome_generator:
                        self.bridge.esphome_generator.save_secrets_template()
                    
                    network_id = controller_data.pop('network_id', None)
                    wifi_ssid = controller_data.pop('wifi_ssid', None)
                    wifi_password = controller_data.pop('wifi_password', None)
                    
                    # Update Home Assistant's secrets.yaml
                    try:
                        # Only use network_id if it's a valid number >= 0
                        if network_id is not None and network_id >= 0:
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
                
                # Add to both controllers list and config
                self.bridge.controllers.append(controller_data)
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
                        # Store esphome_path in controller data
                        controller_data['esphome_path'] = esphome_path
                        self.bridge.save_config()  # Save again with esphome_path
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
        
        @app.route('/api/esphome/devices')
        def get_esphome_devices():
            """Get list of ESPHome devices from /config/esphome/*.yaml"""
            try:
                esphome_dir = '/config/esphome'
                devices = []
                
                if os.path.exists(esphome_dir):
                    for filename in os.listdir(esphome_dir):
                        if filename.endswith('.yaml') and filename != 'secrets.yaml':
                            filepath = os.path.join(esphome_dir, filename)
                            device_name = filename[:-5]  # Remove .yaml extension
                            
                            # Try to read the YAML to get device info
                            try:
                                with open(filepath, 'r') as f:
                                    content = f.read()
                                    # Basic parsing to check if it's a BRMesh controller
                                    is_brmesh = 'fastcon:' in content
                                    
                                devices.append({
                                    'name': device_name,
                                    'filename': filename,
                                    'path': filepath,
                                    'is_brmesh': is_brmesh
                                })
                            except Exception as e:
                                logger.warning(f"Could not read ESPHome config {filename}: {e}")
                
                return jsonify({'devices': devices})
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/esphome/status/<controller_name>')
        def get_esphome_status(controller_name):
            """Get ESPHome device status and firmware version"""
            try:
                import socket
                import requests
                
                # Try to resolve mDNS hostname
                hostname = f"{controller_name}.local"
                ip = None
                online = False
                firmware_version = None
                
                try:
                    ip = socket.gethostbyname(hostname)
                    # Try to connect to ESPHome web server
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2)
                    result = sock.connect_ex((ip, 80))
                    sock.close()
                    online = (result == 0)
                    
                    # Try to fetch firmware version from ESPHome web server
                    if online:
                        try:
                            # ESPHome web server exposes info at /text_sensor/bridge_firmware_version
                            # or we can check the main page for version info
                            resp = requests.get(f'http://{ip}/', timeout=3)
                            if resp.ok:
                                # Try to extract version from HTML comment or global var
                                import re
                                match = re.search(r'ESP BLE Bridge v([\d.]+)', resp.text)
                                if match:
                                    firmware_version = match.group(1)
                        except:
                            pass
                except:
                    pass
                
                # Get expected firmware version from generator
                expected_version = "1.0.0"  # Default
                if self.bridge.esphome_generator:
                    try:
                        # Extract version from generator constant
                        import inspect
                        source = inspect.getsource(self.bridge.esphome_generator.generate_controller_config)
                        match = re.search(r'BRIDGE_FIRMWARE_VERSION = "([\d.]+)"', source)
                        if match:
                            expected_version = match.group(1)
                    except:
                        pass
                
                return jsonify({
                    'name': controller_name,
                    'hostname': hostname,
                    'ip': ip,
                    'online': online,
                    'firmware_version': firmware_version,
                    'expected_version': expected_version,
                    'needs_update': firmware_version is not None and firmware_version != expected_version
                })
            except Exception as e:
                logger.error(f"Failed to get ESPHome status: {e}")
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/esphome/logs/<controller_name>')
        def get_esphome_logs(controller_name):
            """Get recent logs from ESPHome device"""
            try:
                import socket
                import requests
                
                # Try to resolve mDNS hostname
                hostname = f"{controller_name}.local"
                try:
                    ip = socket.gethostbyname(hostname)
                except:
                    return jsonify({'error': 'Controller offline or not found'}), 404
                
                # Fetch logs from ESPHome web server (text format)
                try:
                    resp = requests.get(f'http://{ip}/logs', timeout=5, stream=True)
                    if not resp.ok:
                        return jsonify({'error': 'Failed to fetch logs'}), 500
                    
                    # Read the log stream (ESPHome returns text/event-stream)
                    # We'll collect the first chunk of logs
                    logs_text = ""
                    for chunk in resp.iter_content(chunk_size=8192, decode_unicode=True):
                        if chunk:
                            logs_text += chunk
                            if len(logs_text) > 50000:  # Limit to ~50KB
                                break
                    
                    # Return raw text logs (frontend will display as-is)
                    return jsonify({
                        'logs': logs_text,
                        'raw': True  # Tell frontend this is raw text
                    })
                    
                except requests.exceptions.Timeout:
                    return jsonify({'error': 'Request timed out - controller may be busy'}), 504
                except Exception as e:
                    logger.error(f"Failed to fetch logs: {e}")
                    return jsonify({'error': f'Failed to fetch logs: {str(e)}'}), 500
                    
            except Exception as e:
                logger.error(f"Failed to get ESPHome logs: {e}")
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
                
                # Generate config (includes all lights for mesh network)
                yaml_config = self.bridge.esphome_generator.generate_controller_config(controller)
                
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
        
        @app.route('/api/lights/<int:light_id>/reset', methods=['POST'])
        def factory_reset_light(light_id):
            """Factory reset a light (clears pairing, returns to pairing mode)"""
            try:
                if light_id not in self.bridge.lights:
                    return jsonify({'error': f'Light {light_id} not found'}), 404
                
                logger.info(f"🔄 Factory resetting light {light_id}")
                success = self.bridge.factory_reset_light(light_id)
                
                if success:
                    return jsonify({
                        'success': True,
                        'message': f'Light {light_id} has been factory reset. Power cycle the light to enter pairing mode.'
                    })
                else:
                    return jsonify({'error': 'Failed to send reset command'}), 500
            except Exception as e:
                logger.error(f"Reset light error: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/lights/<int:light_id>/unpair', methods=['POST'])
        def unpair_light(light_id):
            """Remove light from configuration (unregister from Home Assistant)"""
            try:
                if light_id not in self.bridge.lights:
                    return jsonify({'error': f'Light {light_id} not found'}), 404
                
                light_name = self.bridge.lights[light_id]['name']
                logger.info(f"🗑️  Unpairing light {light_id} ({light_name})")
                
                # Remove from MQTT discovery
                self.bridge.unpublish_light_discovery(light_id)
                
                # Remove from lights dictionary
                del self.bridge.lights[light_id]
                
                # Remove from config
                self.bridge.config['lights'] = [
                    light for light in self.bridge.config.get('lights', [])
                    if light['light_id'] != light_id
                ]
                self.bridge.save_config()
                
                # Regenerate ESPHome configs if enabled
                if self.bridge.esphome_generator and self.bridge.config.get('generate_esphome_configs', True):
                    self.bridge.esphome_generator.generate_all_configs()
                
                return jsonify({
                    'success': True,
                    'message': f'Light {light_id} ({light_name}) has been removed from configuration'
                })
            except Exception as e:
                logger.error(f"Unpair light error: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/controllers/<controller_name>/reset', methods=['POST'])
        def reset_controller(controller_name):
            """Reset controller configuration (clears WiFi, regenerates secrets)"""
            try:
                controller = next((c for c in self.bridge.controllers if c['name'] == controller_name), None)
                if not controller:
                    return jsonify({'error': 'Controller not found'}), 404
                
                logger.info(f"🔄 Resetting controller {controller_name}")
                
                # Remove controller from configuration
                self.bridge.controllers = [c for c in self.bridge.controllers if c['name'] != controller_name]
                self.bridge.config['controllers'] = self.bridge.controllers
                self.bridge.save_config()
                
                # Remove ESPHome YAML file
                esphome_path = f'/config/esphome/{controller_name}.yaml'
                if os.path.exists(esphome_path):
                    os.remove(esphome_path)
                    logger.info(f"🗑️  Removed ESPHome config: {esphome_path}")
                
                return jsonify({
                    'success': True,
                    'message': f'Controller {controller_name} has been reset. You can add it again as a new controller.'
                })
            except Exception as e:
                logger.error(f"Reset controller error: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/system/reset', methods=['POST'])
        def system_reset():
            """Full system reset (removes all lights, controllers, scenes, effects - use with caution!)"""
            try:
                data = request.json or {}
                confirm = data.get('confirm', False)
                
                if not confirm:
                    return jsonify({
                        'error': 'System reset requires confirmation. Set "confirm": true in request body.'
                    }), 400
                
                logger.warning("⚠️  FULL SYSTEM RESET INITIATED")
                
                # Remove all MQTT discovery topics
                for light_id in list(self.bridge.lights.keys()):
                    self.bridge.unpublish_light_discovery(light_id)
                
                # Clear all data
                self.bridge.lights = {}
                self.bridge.controllers = []
                
                # Reset config to defaults
                self.bridge.config['lights'] = []
                self.bridge.config['controllers'] = []
                self.bridge.config['scenes'] = []
                self.bridge.config['effects'] = []
                self.bridge.save_config()
                
                # Remove all ESPHome YAML files (except secrets.yaml)
                esphome_dir = '/config/esphome'
                if os.path.exists(esphome_dir):
                    for filename in os.listdir(esphome_dir):
                        if filename.endswith('.yaml') and filename != 'secrets.yaml':
                            filepath = os.path.join(esphome_dir, filename)
                            try:
                                os.remove(filepath)
                                logger.info(f"🗑️  Removed {filepath}")
                            except Exception as e:
                                logger.warning(f"Could not remove {filepath}: {e}")
                
                logger.warning("✅ System reset complete")
                return jsonify({
                    'success': True,
                    'message': 'System has been fully reset. All lights, controllers, scenes, and effects have been removed.'
                })
            except Exception as e:
                logger.error(f"System reset error: {e}", exc_info=True)
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
                options['map_latitude'] = settings.get('latitude', 0)
                options['map_longitude'] = settings.get('longitude', 0)
                options['map_zoom'] = settings.get('zoom', 18)
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
                        from ruamel.yaml import YAML
                        from ruamel.yaml.scalarstring import PlainScalarString
                        yaml = YAML()
                        yaml.preserve_quotes = True
                        yaml.default_flow_style = False
                        
                        secrets_path = '/config/secrets.yaml'
                        secrets = {}
                        
                        # Load existing secrets if file exists
                        if os.path.exists(secrets_path):
                            try:
                                with open(secrets_path, 'r') as f:
                                    secrets = yaml.load(f) or {}
                            except Exception as e:
                                logger.warning(f"Could not read existing secrets.yaml: {e}")
                        
                        # Update mesh_key in secrets (use PlainScalarString to avoid quotes)
                        secrets['mesh_key'] = PlainScalarString(mesh_key)
                        
                        # Save back to file (preserving comments)
                        with open(secrets_path, 'w') as f:
                            yaml.dump(secrets, f)
                        
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
                from ruamel.yaml import YAML
                yaml = YAML()
                yaml.preserve_quotes = True
                yaml.default_flow_style = False
                
                secrets_path = '/config/secrets.yaml'
                
                if not os.path.exists(secrets_path):
                    return jsonify({'networks': []})
                
                with open(secrets_path, 'r') as f:
                    secrets = yaml.load(f) or {}
                
                # Get default network ID (0 if not set)
                default_network_id = secrets.get('default_wifi_network', 0)
                
                # Get all wifi network SSIDs (stored as wifi_network_0, wifi_network_1, etc.)
                networks = []
                i = 0
                while f'wifi_network_{i}_ssid' in secrets:
                    networks.append({
                        'id': i,
                        'ssid': secrets[f'wifi_network_{i}_ssid'],
                        'is_default': (i == default_network_id)
                    })
                    i += 1
                
                # If only one network, automatically make it default
                if len(networks) == 1:
                    networks[0]['is_default'] = True
                
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
                from ruamel.yaml import YAML
                from ruamel.yaml.scalarstring import PlainScalarString
                yaml = YAML()
                yaml.preserve_quotes = True
                yaml.default_flow_style = False
                
                data = request.json
                ssid = data.get('ssid')
                password = data.get('password')
                
                if not ssid or not password:
                    return jsonify({'error': 'SSID and password required'}), 400
                
                secrets_path = '/config/secrets.yaml'
                secrets = {}
                
                logger.info(f"📁 Checking secrets file at: {secrets_path}")
                logger.info(f"📁 File exists: {os.path.exists(secrets_path)}")
                
                if os.path.exists(secrets_path):
                    with open(secrets_path, 'r') as f:
                        secrets = yaml.load(f) or {}
                    logger.info(f"📖 Loaded {len(secrets)} existing secrets")
                else:
                    logger.info(f"📝 Creating new secrets.yaml file")
                
                # Find next available ID
                i = 0
                while f'wifi_network_{i}_ssid' in secrets:
                    i += 1
                
                # Add new network (use PlainScalarString to avoid quotes)
                secrets[f'wifi_network_{i}_ssid'] = PlainScalarString(ssid)
                secrets[f'wifi_network_{i}_password'] = PlainScalarString(password)
                
                logger.info(f"💾 Saving network with ID {i}: {ssid}")
                logger.info(f"💾 Total secrets to save: {len(secrets)}")
                
                # Save with explicit permissions (preserving comments)
                yaml_handler = self._get_yaml_handler()
                with open(secrets_path, 'w') as f:
                    yaml_handler.dump(secrets, f)
                
                # Verify it was written
                if os.path.exists(secrets_path):
                    with open(secrets_path, 'r') as f:
                        verify = yaml.load(f) or {}
                    logger.info(f"✅ Verified: File contains {len(verify)} secrets after save")
                    if f'wifi_network_{i}_ssid' in verify:
                        logger.info(f"✅ Added WiFi network: {ssid} (ID: {i})")
                    else:
                        logger.error(f"❌ Network not found in file after save!")
                else:
                    logger.error(f"❌ secrets.yaml not found after save!")
                
                return jsonify({'success': True, 'id': i, 'ssid': ssid})
            except Exception as e:
                logger.error(f"Failed to add WiFi network: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/wifi-networks/<int:network_id>', methods=['DELETE'])
        def delete_wifi_network(network_id):
            """Delete a WiFi network and reindex remaining networks"""
            try:
                # Prevent deletion of legacy network ID
                if network_id < 0:
                    return jsonify({'error': 'Cannot delete legacy WiFi network. This is a read-only entry from wifi_ssid/wifi_password.'}), 400
                
                from ruamel.yaml import YAML
                from ruamel.yaml.scalarstring import PlainScalarString
                yaml = YAML()
                yaml.preserve_quotes = True
                yaml.default_flow_style = False
                
                secrets_path = '/config/secrets.yaml'
                
                if not os.path.exists(secrets_path):
                    return jsonify({'error': 'No WiFi networks configured'}), 404
                
                with open(secrets_path, 'r') as f:
                    secrets = yaml.load(f) or {}
                
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
                
                # Re-add networks with sequential IDs starting from 0 (use PlainScalarString)
                for idx, network in enumerate(networks):
                    secrets[f'wifi_network_{idx}_ssid'] = PlainScalarString(str(network['ssid']))
                    secrets[f'wifi_network_{idx}_password'] = PlainScalarString(str(network['password']))
                
                # Save (preserving comments)
                yaml_handler = self._get_yaml_handler()
                with open(secrets_path, 'w') as f:
                    yaml_handler.dump(secrets, f)
                
                logger.info(f"🗑️  Deleted WiFi network: {ssid} (reindexed {len(networks)} remaining networks)")
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Failed to delete WiFi network: {e}")
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/wifi-networks/<int:network_id>/set-default', methods=['POST'])
        def set_default_wifi_network(network_id):
            """Set a WiFi network as the default"""
            try:
                from ruamel.yaml import YAML
                from ruamel.yaml.scalarstring import PlainScalarString
                yaml = YAML()
                yaml.preserve_quotes = True
                yaml.default_flow_style = False
                
                secrets_path = '/config/secrets.yaml'
                
                if not os.path.exists(secrets_path):
                    return jsonify({'error': 'No WiFi networks configured'}), 404
                
                with open(secrets_path, 'r') as f:
                    secrets = yaml.load(f) or {}
                
                # Verify network exists
                if f'wifi_network_{network_id}_ssid' not in secrets:
                    return jsonify({'error': 'Network not found'}), 404
                
                # Set default
                secrets['default_wifi_network'] = PlainScalarString(str(network_id))
                
                # Save
                yaml_handler = self._get_yaml_handler()
                with open(secrets_path, 'w') as f:
                    yaml_handler.dump(secrets, f)
                
                logger.info(f"✅ Set WiFi network {network_id} as default")
                return jsonify({'success': True})
            except Exception as e:
                logger.error(f"Failed to set default WiFi network: {e}")
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
        
        @app.route('/api/diagnostics/git-test', methods=['GET'])
        def test_git_connectivity():
            """Test git and GitHub connectivity"""
            try:
                import subprocess
                
                results = {}
                
                # Test 1: Git version
                try:
                    git_version = subprocess.run(
                        ['git', '--version'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    results['git_version'] = git_version.stdout.strip() if git_version.returncode == 0 else f"Error: {git_version.stderr}"
                except Exception as e:
                    results['git_version'] = f"Error: {str(e)}"
                
                # Test 2: Git config
                try:
                    git_config = subprocess.run(
                        ['git', 'config', '--list'],
                        capture_output=True,
                        text=True,
                        timeout=5
                    )
                    results['git_config'] = git_config.stdout if git_config.returncode == 0 else f"Error: {git_config.stderr}"
                except Exception as e:
                    results['git_config'] = f"Error: {str(e)}"
                
                # Test 3: DNS resolution for github.com
                try:
                    dns_test = subprocess.run(
                        ['nslookup', 'github.com'],
                        capture_output=True,
                        text=True,
                        timeout=10
                    )
                    results['dns_github'] = dns_test.stdout if dns_test.returncode == 0 else f"Error: {dns_test.stderr}"
                except Exception as e:
                    results['dns_github'] = f"Error: {str(e)}"
                
                # Test 4: Try to clone the repo (shallow clone)
                try:
                    import tempfile
                    with tempfile.TemporaryDirectory() as tmpdir:
                        clone_test = subprocess.run(
                            ['git', 'clone', '--depth', '1', 'https://github.com/scross01/esphome-fastcon.git', tmpdir],
                            capture_output=True,
                            text=True,
                            timeout=60
                        )
                        results['clone_test'] = {
                            'success': clone_test.returncode == 0,
                            'stdout': clone_test.stdout,
                            'stderr': clone_test.stderr,
                            'returncode': clone_test.returncode
                        }
                except Exception as e:
                    results['clone_test'] = f"Error: {str(e)}"
                
                return jsonify(results)
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/diagnostics/secrets-check', methods=['GET'])
        def check_secrets():
            """Check secrets.yaml for encryption key validity"""
            try:
                from ruamel.yaml import YAML
                yaml = YAML()
                yaml.preserve_quotes = True
                yaml.default_flow_style = False
                secrets_path = '/config/secrets.yaml'
                
                if not os.path.exists(secrets_path):
                    return jsonify({'error': 'secrets.yaml not found'}), 404
                
                with open(secrets_path, 'r') as f:
                    content = f.read()
                    secrets = yaml.load(content)
                
                api_key = secrets.get('api_encryption_key', '')
                ota_pass = secrets.get('ota_password', '')
                
                # Find the raw line in the file
                api_key_line = ''
                for line in content.split('\n'):
                    if line.startswith('api_encryption_key:'):
                        api_key_line = line
                        break
                
                return jsonify({
                    'api_key_value': api_key,
                    'api_key_length': len(api_key),
                    'api_key_raw_line': api_key_line,
                    'ota_password': ota_pass[:10] + '...' if len(ota_pass) > 10 else ota_pass,
                    'total_secrets': len(secrets)
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/diagnostics/esphome-config/<controller_name>')
        def get_esphome_config(controller_name):
            """Get raw ESPHome config to debug formatting"""
            try:
                config_path = f'/config/esphome/{controller_name}.yaml'
                if not os.path.exists(config_path):
                    return jsonify({'error': f'Config not found: {config_path}'}), 404
                
                with open(config_path, 'r') as f:
                    content = f.read()
                
                # Return relevant lines around api section
                lines = content.split('\n')
                result_lines = []
                for i, line in enumerate(lines):
                    if 'api:' in line or 'encryption' in line or 'key:' in line or '!secret' in line:
                        start = max(0, i - 2)
                        end = min(len(lines), i + 3)
                        result_lines.extend(lines[start:end])
                
                return jsonify({
                    'full_config': content,
                    'api_section': '\n'.join(result_lines),
                    'file_path': config_path
                })
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/diagnostics/secrets-raw')
        def get_secrets_raw():
            """Get raw secrets.yaml content to debug formatting issues"""
            try:
                ha_secrets_path = '/config/secrets.yaml'
                esphome_secrets_path = '/config/esphome/secrets.yaml'
                
                result = {}
                
                # Check HA secrets
                if os.path.exists(ha_secrets_path):
                    with open(ha_secrets_path, 'r') as f:
                        content = f.read()
                    lines = content.split('\n')
                    result_lines = []
                    for i, line in enumerate(lines):
                        if 'api_encryption_key' in line or 'ota_password' in line:
                            start = max(0, i - 1)
                            end = min(len(lines), i + 2)
                            result_lines.extend(lines[start:end])
                    result['ha_secrets'] = {
                        'relevant_lines': '\n'.join(result_lines),
                        'file_size': len(content),
                        'total_lines': len(lines)
                    }
                else:
                    result['ha_secrets'] = {'error': 'Not found'}
                
                # Check ESPHome secrets
                if os.path.exists(esphome_secrets_path):
                    with open(esphome_secrets_path, 'r') as f:
                        content = f.read()
                    lines = content.split('\n')
                    result_lines = []
                    for i, line in enumerate(lines):
                        if 'api_encryption_key' in line or 'ota_password' in line:
                            start = max(0, i - 1)
                            end = min(len(lines), i + 2)
                            result_lines.extend(lines[start:end])
                    result['esphome_secrets'] = {
                        'relevant_lines': '\n'.join(result_lines),
                        'file_size': len(content),
                        'total_lines': len(lines)
                    }
                else:
                    result['esphome_secrets'] = {'error': 'Not found'}
                
                return jsonify(result)
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
        
        @app.route('/api/pairing/discover', methods=['GET'])
        def discover_unpaired_devices():
            """Discover BRMesh devices in pairing mode"""
            try:
                if not self.bridge.ble_discovery:
                    logger.warning("BLE discovery not initialized")
                    return jsonify({'error': 'BLE discovery not enabled'}), 400
                
                logger.info("Starting BLE scan for unpaired devices (15 second scan)...")
                
                # Run async BLE scan with longer duration for pairing
                import asyncio
                try:
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    devices = loop.run_until_complete(
                        self.bridge.ble_discovery.scan_for_devices(duration=15)
                    )
                    loop.close()
                except Exception as scan_error:
                    logger.error(f"BLE scan failed: {scan_error}", exc_info=True)
                    return jsonify({'error': f'BLE scan failed: {str(scan_error)}'}), 500
                
                # Format for frontend
                unpaired_devices = [
                    {
                        'mac': d['mac_address'],
                        'rssi': d['rssi'],
                        'name': d['name'],
                        'manufacturer': 'BRMesh'
                    }
                    for d in devices
                ]
                
                logger.info(f"Found {len(unpaired_devices)} unpaired devices: {[d['mac'] for d in unpaired_devices]}")
                return jsonify(unpaired_devices)
            except Exception as e:
                logger.error(f"Error discovering unpaired devices: {e}", exc_info=True)
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/pairing/pair', methods=['POST'])
        def pair_device():
            """Pair a BRMesh device
            
            Expected POST data:
            {
                "mac": "AA:BB:CC:DD:EE:FF",
                "address": 1,
                "group_id": 1,
                "mesh_key": "30323336"
            }
            """
            try:
                data = request.json
                mac = data.get('mac')
                address = data.get('address', 1)
                group_id = data.get('group_id', 1)
                mesh_key = data.get('mesh_key')
                
                if not mac:
                    return jsonify({'error': 'MAC address is required'}), 400
                
                # Get mesh key from config if not provided
                if not mesh_key:
                    mesh_key = self.bridge.config.get('mesh_key', '30323336')
                
                # Convert mesh key string to bytes
                if isinstance(mesh_key, str):
                    mesh_key_bytes = bytes.fromhex(mesh_key) if len(mesh_key) == 8 else mesh_key.encode('utf-8')
                else:
                    mesh_key_bytes = mesh_key
                
                # Generate pairing response
                pairing_response = create_pairing_response(
                    device_mac=mac,
                    address=address,
                    group_id=group_id,
                    mesh_key=mesh_key_bytes
                )
                
                logger.info(f"Generated pairing response for {mac}: {pairing_response.hex()}")
                
                # TODO: Send pairing response via BLE
                # For now, just return the response
                
                # Add device to lights config
                light_config = {
                    'id': len(self.bridge.config.get('lights', [])) + 1,
                    'address': address,
                    'name': f'Light {address}',
                    'mac': mac,
                    'group_id': group_id,
                    'paired': True
                }
                
                if 'lights' not in self.bridge.config:
                    self.bridge.config['lights'] = []
                self.bridge.config['lights'].append(light_config)
                self.bridge.save_config()
                
                return jsonify({
                    'success': True,
                    'message': f'Device {mac} paired successfully',
                    'pairing_response': pairing_response.hex(),
                    'light': light_config
                })
                
            except Exception as e:
                logger.error(f"Error pairing device: {e}")
                return jsonify({'error': str(e)}), 500
        
        @app.route('/api/control/send', methods=['POST'])
        def send_control_command():
            """Send a control command to a light
            
            Expected POST data:
            {
                "address": 1,
                "command_type": 1,  // 0=status, 1=control, 2=pairing, 3=group, 4=scene
                "payload": "0164ffffff",  // hex string
                "seq": 0
            }
            """
            try:
                data = request.json
                address = data.get('address')
                cmd_type = data.get('command_type', 1)
                payload_hex = data.get('payload', '')
                seq = data.get('seq', 0)
                
                if address is None:
                    return jsonify({'error': 'Address is required'}), 400
                
                # Get mesh key from config
                mesh_key = self.bridge.config.get('mesh_key', '30323336')
                if isinstance(mesh_key, str):
                    mesh_key_bytes = bytes.fromhex(mesh_key) if len(mesh_key) == 8 else mesh_key.encode('utf-8')
                else:
                    mesh_key_bytes = mesh_key
                
                # Convert payload hex to bytes
                payload = bytes.fromhex(payload_hex) if payload_hex else bytes()
                
                # Check if mesh forwarding should be enabled (default: True)
                mesh_forward = data.get('mesh_forward', True)
                
                # Generate control command
                command = create_control_command(
                    address=address,
                    cmd_type=cmd_type,
                    payload=payload,
                    mesh_key=mesh_key_bytes,
                    seq=seq,
                    forward=1 if mesh_forward else 0
                )
                
                logger.info(f"Generated control command for address {address} (forward={1 if mesh_forward else 0}): {command.hex()}")
                
                # TODO: Send command via BLE
                
                return jsonify({
                    'success': True,
                    'command': command.hex(),
                    'length': len(command)
                })
                
            except Exception as e:
                logger.error(f"Error sending control command: {e}")
                return jsonify({'error': str(e)}), 500
    
    def run(self, host='0.0.0.0', port=8099):
        """Run the web UI"""
        app.run(host=host, port=port, debug=False)
