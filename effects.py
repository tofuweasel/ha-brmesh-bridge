#!/usr/bin/env python3
"""
BRMesh Effects Engine - Dynamic color effects and scenes
"""
import asyncio
import colorsys
import math
import random
import time
from typing import List, Dict, Tuple
import logging

logger = logging.getLogger(__name__)

class BRMeshEffects:
    """Dynamic lighting effects for BRMesh lights"""
    
    def __init__(self, bridge):
        self.bridge = bridge
        self.running_effects = {}
        self.effect_tasks = {}
    
    async def start_effect(self, light_ids: List[int], effect_name: str, **kwargs):
        """Start an effect on given lights"""
        effect_id = f"{effect_name}_{'-'.join(map(str, light_ids))}"
        
        if effect_id in self.running_effects:
            await self.stop_effect(effect_id)
        
        self.running_effects[effect_id] = True
        
        if effect_name == "rainbow":
            task = asyncio.create_task(self.rainbow_effect(light_ids, **kwargs))
        elif effect_name == "color_loop":
            task = asyncio.create_task(self.color_loop_effect(light_ids, **kwargs))
        elif effect_name == "twinkle":
            task = asyncio.create_task(self.twinkle_effect(light_ids, **kwargs))
        elif effect_name == "fire":
            task = asyncio.create_task(self.fire_effect(light_ids, **kwargs))
        elif effect_name == "christmas":
            task = asyncio.create_task(self.christmas_effect(light_ids, **kwargs))
        elif effect_name == "halloween":
            task = asyncio.create_task(self.halloween_effect(light_ids, **kwargs))
        elif effect_name == "strobe":
            task = asyncio.create_task(self.strobe_effect(light_ids, **kwargs))
        elif effect_name == "breathe":
            task = asyncio.create_task(self.breathe_effect(light_ids, **kwargs))
        else:
            logger.warning(f"Unknown effect: {effect_name}")
            return
        
        self.effect_tasks[effect_id] = task
        logger.info(f"Started effect '{effect_name}' for lights {light_ids}")
    
    async def stop_effect(self, effect_id: str):
        """Stop a running effect"""
        if effect_id in self.running_effects:
            self.running_effects[effect_id] = False
            if effect_id in self.effect_tasks:
                task = self.effect_tasks[effect_id]
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass
                del self.effect_tasks[effect_id]
            del self.running_effects[effect_id]
            logger.info(f"Stopped effect {effect_id}")
    
    async def rainbow_effect(self, light_ids: List[int], speed: float = 50, brightness: int = 255):
        """Smooth rainbow cycle across all lights"""
        effect_id = f"rainbow_{'-'.join(map(str, light_ids))}"
        hue_offset = 0
        
        while self.running_effects.get(effect_id, False):
            for i, light_id in enumerate(light_ids):
                # Calculate hue for this light
                hue = (hue_offset + (i * 360 / len(light_ids))) % 360
                rgb = self.hsv_to_rgb(hue / 360, 1.0, brightness / 255)
                
                await self.bridge.set_light_color(light_id, rgb, brightness, True)
            
            hue_offset = (hue_offset + speed / 10) % 360
            await asyncio.sleep(0.1)
    
    async def color_loop_effect(self, light_ids: List[int], colors: List[Tuple[int, int, int]] = None, interval: float = 2.0):
        """Cycle through predefined colors"""
        effect_id = f"color_loop_{'-'.join(map(str, light_ids))}"
        
        if colors is None:
            colors = [
                (255, 0, 0),    # Red
                (255, 127, 0),  # Orange
                (255, 255, 0),  # Yellow
                (0, 255, 0),    # Green
                (0, 0, 255),    # Blue
                (75, 0, 130),   # Indigo
                (148, 0, 211),  # Violet
            ]
        
        color_index = 0
        while self.running_effects.get(effect_id, False):
            rgb = colors[color_index]
            
            for light_id in light_ids:
                await self.bridge.set_light_color(light_id, rgb, 255, True)
            
            color_index = (color_index + 1) % len(colors)
            await asyncio.sleep(interval)
    
    async def twinkle_effect(self, light_ids: List[int], color: Tuple[int, int, int] = (255, 255, 255), speed: float = 1.0):
        """Random twinkling lights"""
        effect_id = f"twinkle_{'-'.join(map(str, light_ids))}"
        
        while self.running_effects.get(effect_id, False):
            # Pick random lights to twinkle
            num_twinkles = max(1, len(light_ids) // 3)
            twinkle_lights = random.sample(light_ids, num_twinkles)
            
            # Brighten selected lights
            for light_id in twinkle_lights:
                brightness = random.randint(150, 255)
                await self.bridge.set_light_color(light_id, color, brightness, True)
            
            # Dim others
            for light_id in light_ids:
                if light_id not in twinkle_lights:
                    await self.bridge.set_light_color(light_id, color, 50, True)
            
            await asyncio.sleep(0.3 / speed)
    
    async def fire_effect(self, light_ids: List[int], intensity: float = 1.0):
        """Flickering fire effect"""
        effect_id = f"fire_{'-'.join(map(str, light_ids))}"
        
        while self.running_effects.get(effect_id, False):
            for light_id in light_ids:
                # Random red-orange-yellow colors
                r = random.randint(200, 255)
                g = random.randint(50, int(150 * intensity))
                b = 0
                brightness = random.randint(150, 255)
                
                await self.bridge.set_light_color(light_id, (r, g, b), brightness, True)
            
            await asyncio.sleep(random.uniform(0.05, 0.15))
    
    async def christmas_effect(self, light_ids: List[int], interval: float = 1.0):
        """Red and green alternating Christmas lights"""
        effect_id = f"christmas_{'-'.join(map(str, light_ids))}"
        
        red = (255, 0, 0)
        green = (0, 255, 0)
        white = (255, 255, 255)
        colors = [red, green, white]
        
        offset = 0
        while self.running_effects.get(effect_id, False):
            for i, light_id in enumerate(light_ids):
                color = colors[(i + offset) % len(colors)]
                await self.bridge.set_light_color(light_id, color, 255, True)
            
            offset = (offset + 1) % len(colors)
            await asyncio.sleep(interval)
    
    async def halloween_effect(self, light_ids: List[int], interval: float = 0.5):
        """Orange and purple Halloween theme"""
        effect_id = f"halloween_{'-'.join(map(str, light_ids))}"
        
        orange = (255, 100, 0)
        purple = (128, 0, 128)
        
        toggle = True
        while self.running_effects.get(effect_id, False):
            color = orange if toggle else purple
            
            for light_id in light_ids:
                await self.bridge.set_light_color(light_id, color, 255, True)
            
            toggle = not toggle
            await asyncio.sleep(interval)
    
    async def strobe_effect(self, light_ids: List[int], color: Tuple[int, int, int] = (255, 255, 255), frequency: float = 10):
        """Strobe/flash effect"""
        effect_id = f"strobe_{'-'.join(map(str, light_ids))}"
        interval = 1.0 / (frequency * 2)  # On and off
        
        toggle = True
        while self.running_effects.get(effect_id, False):
            brightness = 255 if toggle else 0
            
            for light_id in light_ids:
                await self.bridge.set_light_color(light_id, color, brightness, toggle)
            
            toggle = not toggle
            await asyncio.sleep(interval)
    
    async def breathe_effect(self, light_ids: List[int], color: Tuple[int, int, int] = (255, 255, 255), speed: float = 1.0):
        """Smooth breathing/pulsing effect"""
        effect_id = f"breathe_{'-'.join(map(str, light_ids))}"
        
        phase = 0
        while self.running_effects.get(effect_id, False):
            # Sine wave for smooth breathing
            brightness = int((math.sin(phase) + 1) * 127.5)
            
            for light_id in light_ids:
                await self.bridge.set_light_color(light_id, color, brightness, True)
            
            phase += 0.1 * speed
            await asyncio.sleep(0.05)
    
    @staticmethod
    def hsv_to_rgb(h: float, s: float, v: float) -> Tuple[int, int, int]:
        """Convert HSV to RGB"""
        r, g, b = colorsys.hsv_to_rgb(h, s, v)
        return (int(r * 255), int(g * 255), int(b * 255))
    
    async def apply_scene(self, scene: Dict):
        """Apply a saved scene"""
        logger.info(f"Applying scene: {scene['name']}")
        
        for light_config in scene['lights']:
            light_id = light_config['light_id']
            state = light_config.get('state', True)
            brightness = light_config.get('brightness', 255)
            rgb = tuple(light_config.get('rgb', [255, 255, 255]))
            
            await self.bridge.set_light_color(light_id, rgb, brightness, state)
