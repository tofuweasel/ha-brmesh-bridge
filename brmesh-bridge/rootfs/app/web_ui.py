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
        
        @app.route('/api/scenes/<scene_name>', methods=['POST'])
        def apply_scene(scene_name):
            """Apply a saved scene"""
            try:
                with open('/data/options.json', 'r') as f:
                    config = json.load(f)
                
                scenes = config.get('scenes', [])
                scene = next((s for s in scenes if s['name'] == scene_name), None)
                
                if scene:
                    self.bridge.effects.apply_scene(scene)
                    return jsonify({'success': True})
                return jsonify({'error': 'Scene not found'}), 404
            except Exception as e:
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
                # Run BLE discovery if available
                if self.bridge.ble_discovery:
                    import asyncio
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    new_lights = loop.run_until_complete(
                        self.bridge.ble_discovery.auto_discover_and_register(duration=30)
                    )
                    loop.close()
                    return jsonify({'lights': new_lights, 'count': len(new_lights)})
                else:
                    return jsonify({'error': 'BLE discovery not enabled'}), 400
            except Exception as e:
                return jsonify({'error': str(e)}), 500
        
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
                options['mesh_key'] = settings.get('mesh_key', options.get('mesh_key', ''))
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
