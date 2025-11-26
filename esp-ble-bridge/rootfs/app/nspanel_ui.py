#!/usr/bin/env python3
"""
NSPanel TFT UI Generator for BRMesh Lights
Generates Nextion HMI commands to display light controls on NSPanel
"""
import logging
from typing import Dict, List, Optional
import json

logger = logging.getLogger(__name__)

class NSPanelUIGenerator:
    """
    Generate NSPanel interface for BRMesh light control
    
    NSPanel uses Nextion display protocol
    We can send commands via MQTT or UART to update the display
    """
    
    def __init__(self, bridge):
        self.bridge = bridge
        self.nspanel_entity = bridge.config.get('nspanel_entity_id', '')
        self.page_id = 10  # Custom page for BRMesh lights
        
        # Color palette
        self.colors = {
            'background': 0x0000,      # Black
            'card_bg': 0x2945,         # Dark gray
            'text': 0xFFFF,            # White
            'accent': 0x07E0,          # Green
            'off': 0x7BEF,             # Light gray
            'on': 0xFFE0               # Yellow
        }
    
    def generate_page_layout(self) -> List[str]:
        """
        Generate NSPanel page layout for light grid
        
        Returns list of Nextion commands to set up the page
        """
        commands = []
        
        # Switch to custom page
        commands.append(f"page {self.page_id}")
        
        # Set background
        commands.append(f"cls {self.colors['background']}")
        
        # Header
        commands.append(f'xstr 10,5,460,30,2,{self.colors["text"]},{self.colors["background"]},1,1,1,"BRMesh Lights"')
        
        # Grid layout: 4 columns x N rows
        lights_list = list(self.bridge.lights.items())
        cols = 4
        rows = (len(lights_list) + cols - 1) // cols
        
        card_width = 110
        card_height = 100
        gap = 10
        start_x = 10
        start_y = 50
        
        for idx, (light_id, light) in enumerate(lights_list):
            row = idx // cols
            col = idx % cols
            
            x = start_x + col * (card_width + gap)
            y = start_y + row * (card_height + gap)
            
            # Draw light card
            commands.extend(self._generate_light_card(light_id, light, x, y, card_width, card_height))
        
        # Navigation buttons
        commands.append(f'xstr 10,430,100,30,1,{self.colors["text"]},{self.colors["accent"]},1,1,1,"< Back"')
        commands.append(f'xstr 370,430,100,30,1,{self.colors["text"]},{self.colors["accent"]},1,1,1,"Effects >"')
        
        return commands
    
    def _generate_light_card(self, light_id: int, light: Dict, x: int, y: int, w: int, h: int) -> List[str]:
        """Generate UI elements for a single light card"""
        commands = []
        
        state = light['state']
        is_on = state.get('state', False)
        name = light['name']
        
        # Truncate long names
        if len(name) > 12:
            name = name[:10] + '..'
        
        # Card background
        bg_color = self.colors['on'] if is_on else self.colors['card_bg']
        commands.append(f"fill {x},{y},{w},{h},{bg_color}")
        commands.append(f"draw {x},{y},{x+w},{y+h},{self.colors['text']}")
        
        # Light icon
        icon_x = x + w // 2 - 15
        icon_y = y + 10
        icon_color = self.colors['text'] if is_on else self.colors['off']
        
        # Draw bulb icon (simplified)
        commands.append(f"cir {icon_x + 15},{icon_y + 20},15,{icon_color}")
        
        # Light name
        text_y = y + h - 35
        commands.append(f'xstr {x+5},{text_y},{w-10},20,0,{self.colors["text"]},{bg_color},1,1,1,"{name}"')
        
        # ID label (smaller)
        id_y = y + h - 15
        commands.append(f'xstr {x+5},{id_y},{w-10},12,0,{self.colors["off"]},{bg_color},0,1,1,"ID: {light_id}"')
        
        # Touch hotspot for toggling
        commands.append(f"// Touch area for light {light_id}: {x},{y},{w},{h}")
        
        return commands
    
    def generate_effects_page(self) -> List[str]:
        """Generate effects selection page"""
        commands = []
        
        commands.append(f"page {self.page_id + 1}")
        commands.append(f"cls {self.colors['background']}")
        
        # Header
        commands.append(f'xstr 10,5,460,30,2,{self.colors["text"]},{self.colors["background"]},1,1,1,"Light Effects"')
        
        # Effect buttons
        effects = [
            "Rainbow", "Color Loop", "Twinkle", "Fire",
            "Christmas", "Halloween", "Strobe", "Breathe"
        ]
        
        btn_width = 220
        btn_height = 50
        gap = 10
        start_x = 10
        start_y = 50
        
        for idx, effect in enumerate(effects):
            row = idx // 2
            col = idx % 2
            
            x = start_x + col * (btn_width + gap)
            y = start_y + row * (btn_height + gap)
            
            # Button background
            commands.append(f"fill {x},{y},{btn_width},{btn_height},{self.colors['accent']}")
            commands.append(f'xstr {x+10},{y+15},{btn_width-20},{btn_height-30},1,{self.colors["text"]},{self.colors["accent"]},1,1,1,"{effect}"')
        
        # Back button
        commands.append(f'xstr 10,430,100,30,1,{self.colors["text"]},{self.colors["accent"]},1,1,1,"< Back"')
        
        return commands
    
    def update_light_state(self, light_id: int) -> List[str]:
        """Generate commands to update a single light's display"""
        if light_id not in self.bridge.lights:
            return []
        
        light = self.bridge.lights[light_id]
        
        # Find light position in grid
        lights_list = list(self.bridge.lights.keys())
        idx = lights_list.index(light_id)
        
        cols = 4
        row = idx // cols
        col = idx % cols
        
        card_width = 110
        card_height = 100
        gap = 10
        start_x = 10
        start_y = 50
        
        x = start_x + col * (card_width + gap)
        y = start_y + row * (card_height + gap)
        
        # Redraw just this card
        return self._generate_light_card(light_id, light, x, y, card_width, card_height)
    
    def send_to_nspanel(self, commands: List[str]) -> bool:
        """
        Send Nextion commands to NSPanel via Home Assistant
        
        Uses MQTT or ESPHome service call
        """
        if not self.nspanel_entity:
            logger.warning("NSPanel entity not configured")
            return False
        
        try:
            # Method 1: Via MQTT (if NSPanel uses MQTT)
            if self.bridge.mqtt_client:
                for cmd in commands:
                    topic = f"{self.nspanel_entity}/command"
                    self.bridge.mqtt_client.publish(topic, cmd)
                logger.info(f"Sent {len(commands)} commands to NSPanel via MQTT")
                return True
            
            # Method 2: Via Home Assistant service call (if using ESPHome)
            # This would require Home Assistant API integration
            logger.warning("NSPanel communication method not available")
            return False
            
        except Exception as e:
            logger.error(f"Failed to send to NSPanel: {e}")
            return False
    
    def initialize_nspanel_ui(self) -> bool:
        """Initialize NSPanel with BRMesh light interface"""
        if not self.bridge.config.get('enable_nspanel_ui', False):
            return False
        
        logger.info("Initializing NSPanel UI...")
        
        # Generate and send page layout
        layout_commands = self.generate_page_layout()
        success = self.send_to_nspanel(layout_commands)
        
        if success:
            logger.info("NSPanel UI initialized successfully")
        
        return success
    
    def refresh_nspanel_display(self):
        """Refresh all light states on NSPanel"""
        if not self.bridge.config.get('enable_nspanel_ui', False):
            return
        
        # Redraw entire page
        commands = self.generate_page_layout()
        self.send_to_nspanel(commands)
    
    def handle_nspanel_touch(self, touch_x: int, touch_y: int) -> Optional[int]:
        """
        Handle touch event from NSPanel
        
        Determine which light was touched based on coordinates
        Returns light_id if touch was on a light card
        """
        lights_list = list(self.bridge.lights.keys())
        
        cols = 4
        card_width = 110
        card_height = 100
        gap = 10
        start_x = 10
        start_y = 50
        
        for idx, light_id in enumerate(lights_list):
            row = idx // cols
            col = idx % cols
            
            x = start_x + col * (card_width + gap)
            y = start_y + row * (card_height + gap)
            
            # Check if touch is within this card
            if x <= touch_x <= x + card_width and y <= touch_y <= y + card_height:
                return light_id
        
        return None
    
    def generate_tft_upload_file(self, output_path: str):
        """
        Generate a complete TFT file for NSPanel
        
        This is for advanced users who want to customize the display
        Requires Nextion Editor to compile
        """
        # This would generate a full .HMI project file
        # For now, just document the structure
        
        tft_config = {
            'page_id': self.page_id,
            'page_name': 'brmesh_lights',
            'components': [],
            'events': []
        }
        
        lights_list = list(self.bridge.lights.items())
        cols = 4
        
        for idx, (light_id, light) in enumerate(lights_list):
            row = idx // cols
            col = idx % cols
            
            x = 10 + col * 120
            y = 50 + row * 110
            
            # Button component for each light
            tft_config['components'].append({
                'type': 'button',
                'id': f'btn_light_{light_id}',
                'x': x,
                'y': y,
                'w': 110,
                'h': 100,
                'text': light['name'],
                'event': f'toggle_light_{light_id}'
            })
            
            # Touch event
            tft_config['events'].append({
                'component': f'btn_light_{light_id}',
                'event': 'Touch Release',
                'action': f'mqtt_publish("brmesh/light/{light_id}/toggle")'
            })
        
        # Save config
        try:
            with open(output_path, 'w') as f:
                json.dump(tft_config, f, indent=2)
            logger.info(f"Generated TFT config: {output_path}")
        except Exception as e:
            logger.error(f"Failed to generate TFT file: {e}")
