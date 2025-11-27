"""
BRMesh Effects Protocol Implementation
Autonomous and app-driven lighting effects for BRMesh lights
"""

import colorsys
import time
from typing import List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class Effect:
    """Represents a BRMesh lighting effect"""
    name: str
    colors: List[Tuple[int, int, int]]
    speed: int  # 0x01 (fast) to 0xFF (slow), ~16ms per unit
    autonomous: bool = True  # True for 0x00 0x52, False for app-driven 0x93


class EffectBuilder:
    """Build BRMesh effect commands"""
    
    # Effect mode bytes for 0x93 commands
    MODE_RAINBOW = 0xf8
    MODE_COMPLEMENTARY = 0xc1
    MODE_DIRECT = 0xff  # No mode byte, direct color
    
    @staticmethod
    def create_autonomous_effect(colors: List[Tuple[int, int, int]], speed: int = 0x30) -> bytes:
        """
        Create autonomous effect command (0x00 0x52)
        Effect runs independently in the light after single command
        
        Args:
            colors: List of (R, G, B) tuples, max 3-4 colors
            speed: Transition speed, 0x01 (fast ~16ms) to 0xFF (slow ~4s)
                   Recommended: 0x01-0x10 (fast), 0x20-0x40 (medium), 0x50+ (slow)
        
        Returns:
            16-byte command payload
        """
        if not colors or len(colors) > 4:
            raise ValueError("Must provide 1-4 colors")
        
        if not 0x01 <= speed <= 0xFF:
            raise ValueError("Speed must be 0x01-0xFF")
        
        num_colors = len(colors)
        payload = [0x00, 0x52, 0x04, num_colors, speed]
        
        # Add RGB values for each color
        for r, g, b in colors:
            payload.extend([r & 0xFF, g & 0xFF, b & 0xFF])
        
        # Pad to 16 bytes total
        while len(payload) < 16:
            payload.append(0x00)
        
        return bytes(payload[:16])
    
    @staticmethod
    def create_color_command(
        target: Tuple[int, int],
        r: int, g: int, b: int,
        mode: Optional[int] = None
    ) -> bytes:
        """
        Create app-driven color command (0x93)
        Used for rapid updates in rainbow/music mode
        
        Args:
            target: (byte1, byte2) target address, e.g., (0x2a, 0xa8) for group
            r, g, b: RGB color values 0-255
            mode: Effect mode (MODE_RAINBOW, MODE_COMPLEMENTARY, or None for direct)
        
        Returns:
            12-byte command payload
        """
        addr1, addr2 = target
        
        if mode is not None:
            # Mode-based command: 93 [target] 04 [mode] [R] [G] [B] 00 00 00 00
            payload = [0x93, addr1, addr2, 0x04, mode, r, g, b, 0x00, 0x00, 0x00, 0x00]
        else:
            # Direct color: 93 [target] 04 ff [R] [G] [B] 00 00 00 00
            payload = [0x93, addr1, addr2, 0x04, 0xff, r, g, b, 0x00, 0x00, 0x00, 0x00]
        
        return bytes(payload)


class EffectPresets:
    """Pre-defined effect presets matching BRMesh app"""
    
    @staticmethod
    def rainbow_loop(speed: int = 0x30) -> Effect:
        """3-color rainbow: Red -> Green -> Blue"""
        return Effect(
            name="Rainbow Loop",
            colors=[(255, 0, 0), (0, 255, 0), (0, 0, 255)],
            speed=speed,
            autonomous=True
        )
    
    @staticmethod
    def warm_cool_fade(speed: int = 0x40) -> Effect:
        """Warm to cool white fade"""
        return Effect(
            name="Warm/Cool Fade",
            colors=[(255, 147, 41), (201, 226, 255)],
            speed=speed,
            autonomous=True
        )
    
    @staticmethod
    def fire(speed: int = 0x10) -> Effect:
        """Fire effect: Red, Orange, Yellow"""
        return Effect(
            name="Fire",
            colors=[(255, 0, 0), (255, 100, 0), (255, 200, 0)],
            speed=speed,
            autonomous=True
        )
    
    @staticmethod
    def ocean(speed: int = 0x40) -> Effect:
        """Ocean waves: Blues and cyans"""
        return Effect(
            name="Ocean",
            colors=[(0, 100, 255), (0, 200, 255), (0, 255, 200)],
            speed=speed,
            autonomous=True
        )
    
    @staticmethod
    def strobe(speed: int = 0x02) -> Effect:
        """Fast white/black strobe"""
        return Effect(
            name="Strobe",
            colors=[(255, 255, 255), (0, 0, 0)],
            speed=speed,
            autonomous=True
        )
    
    @staticmethod
    def police(speed: int = 0x08) -> Effect:
        """Red/Blue police lights"""
        return Effect(
            name="Police",
            colors=[(255, 0, 0), (0, 0, 255)],
            speed=speed,
            autonomous=True
        )


class AppDrivenEffects:
    """App-driven effects that require continuous updates"""
    
    def __init__(self, send_command_callback):
        """
        Args:
            send_command_callback: Function to send mesh commands, signature: f(bytes) -> None
        """
        self.send_command = send_command_callback
        self.running = False
    
    def stop(self):
        """Stop any running effect"""
        self.running = False
    
    def rainbow(self, target: Tuple[int, int], duration: float = 60.0, update_interval: float = 0.3):
        """
        Rainbow color cycle effect
        
        Args:
            target: Target address (e.g., (0x2a, 0xa8) for group)
            duration: How long to run in seconds (0 = infinite)
            update_interval: Time between color updates in seconds
        """
        self.running = True
        start_time = time.time()
        hue = 0.0
        
        try:
            while self.running:
                if duration > 0 and (time.time() - start_time) >= duration:
                    break
                
                # Convert HSV to RGB (full saturation and value)
                r, g, b = colorsys.hsv_to_rgb(hue, 1.0, 1.0)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                
                # Send color command with rainbow mode
                cmd = EffectBuilder.create_color_command(
                    target, r, g, b, mode=EffectBuilder.MODE_RAINBOW
                )
                self.send_command(cmd)
                
                # Increment hue for smooth transition
                hue = (hue + 0.05) % 1.0  # 5% increment = 20 steps per full cycle
                time.sleep(update_interval)
                
        except Exception as e:
            print(f"Rainbow effect error: {e}")
        finally:
            self.running = False
    
    def complementary(self, target: Tuple[int, int], duration: float = 60.0, update_interval: float = 0.5):
        """
        Complementary color effect (alternating opposite colors)
        
        Args:
            target: Target address
            duration: How long to run in seconds (0 = infinite)
            update_interval: Time between color updates in seconds
        """
        self.running = True
        start_time = time.time()
        hue = 0.0
        
        # Complementary colors are 180° apart on color wheel
        colors = [
            (0.0, "Red/Cyan"),       # Red -> Cyan
            (0.33, "Green/Magenta"), # Green -> Magenta
            (0.66, "Blue/Yellow"),   # Blue -> Yellow
        ]
        color_idx = 0
        use_complement = False
        
        try:
            while self.running:
                if duration > 0 and (time.time() - start_time) >= duration:
                    break
                
                # Get current color pair
                base_hue, _ = colors[color_idx]
                current_hue = (base_hue + 0.5) if use_complement else base_hue
                
                r, g, b = colorsys.hsv_to_rgb(current_hue, 1.0, 1.0)
                r, g, b = int(r * 255), int(g * 255), int(b * 255)
                
                # Send color command with complementary mode
                cmd = EffectBuilder.create_color_command(
                    target, r, g, b, mode=EffectBuilder.MODE_COMPLEMENTARY
                )
                self.send_command(cmd)
                
                # Toggle between color and its complement
                use_complement = not use_complement
                if use_complement:
                    color_idx = (color_idx + 1) % len(colors)
                
                time.sleep(update_interval)
                
        except Exception as e:
            print(f"Complementary effect error: {e}")
        finally:
            self.running = False
    
    def music_reactive(
        self,
        target: Tuple[int, int],
        audio_analyzer_callback,
        duration: float = 60.0,
        update_interval: float = 0.1
    ):
        """
        Music-reactive effect (requires audio input)
        
        Args:
            target: Target address
            audio_analyzer_callback: Function that returns (bass, mid, treble) values 0.0-1.0
            duration: How long to run in seconds (0 = infinite)
            update_interval: Time between updates in seconds (0.1 = 10fps)
        """
        self.running = True
        start_time = time.time()
        
        try:
            while self.running:
                if duration > 0 and (time.time() - start_time) >= duration:
                    break
                
                # Get frequency analysis from callback
                bass, mid, treble = audio_analyzer_callback()
                
                # Map frequency bands to RGB
                r = int(bass * 255)      # Bass -> Red
                g = int(mid * 255)       # Mid -> Green
                b = int(treble * 255)    # Treble -> Blue
                
                # Send direct color command (no mode byte for music)
                cmd = EffectBuilder.create_color_command(target, r, g, b, mode=None)
                self.send_command(cmd)
                
                time.sleep(update_interval)
                
        except Exception as e:
            print(f"Music reactive effect error: {e}")
        finally:
            self.running = False


# Example usage and testing
if __name__ == "__main__":
    # Test autonomous effect creation
    print("=== Autonomous Effect Commands ===")
    
    # Rainbow loop
    rainbow = EffectPresets.rainbow_loop(speed=0x30)
    cmd = EffectBuilder.create_autonomous_effect(rainbow.colors, rainbow.speed)
    print(f"Rainbow: {cmd.hex()}")
    
    # Fire effect
    fire = EffectPresets.fire(speed=0x10)
    cmd = EffectBuilder.create_autonomous_effect(fire.colors, fire.speed)
    print(f"Fire: {cmd.hex()}")
    
    # Strobe effect
    strobe = EffectPresets.strobe(speed=0x02)
    cmd = EffectBuilder.create_autonomous_effect(strobe.colors, strobe.speed)
    print(f"Strobe: {cmd.hex()}")
    
    print("\n=== App-Driven Color Commands ===")
    
    # Rainbow mode color (for app-driven rainbow)
    target = (0x2a, 0xa8)  # Group address
    cmd = EffectBuilder.create_color_command(target, 255, 0, 0, mode=EffectBuilder.MODE_RAINBOW)
    print(f"Rainbow Red: {cmd.hex()}")
    
    # Complementary mode
    cmd = EffectBuilder.create_color_command(target, 0, 255, 255, mode=EffectBuilder.MODE_COMPLEMENTARY)
    print(f"Complementary Cyan: {cmd.hex()}")
    
    # Direct color (music mode)
    cmd = EffectBuilder.create_color_command(target, 128, 64, 200, mode=None)
    print(f"Direct Color: {cmd.hex()}")
