from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import Tuple, Optional


class SF6Renderer:
    
    def __init__(self, width: int = 1920, height: int = 1080):
        self.width = width
        self.height = height
        
        self.p1_hp_target = 100.0
        self.p1_hp_display = 100.0
        self.p2_hp_target = 100.0
        self.p2_hp_display = 100.0
        
        self.p1_drive = 6
        self.p2_drive = 6
        
        self.bar_width = 600
        self.bar_height = 25
        self.bar_skew = 20
        
        self.p1_x = 50
        self.p2_x = width - 50 - self.bar_width
        
        self.y_pos = 60
        
        self.colors = {
            'bg': (40, 40, 40, 51),
            'damage': (200, 50, 50, 255),
            'health': (240, 200, 30, 255),
            'drive': (50, 200, 100, 255),
            'drive_empty': (80, 80, 80, 255),
            'text': (255, 255, 255, 255)
        }
    
    def set_hp(self, player: int, target: float, display: Optional[float] = None):
        if player == 1:
            self.p1_hp_target = target
            if display is not None:
                self.p1_hp_display = display
        else:
            self.p2_hp_target = target
            if display is not None:
                self.p2_hp_display = display
    
    def set_drive(self, player: int, value: int):
        if player == 1:
            self.p1_drive = value
        else:
            self.p2_drive = value
    
    def _skewed_rect_coords(self, x: int, y: int, w: int, h: int, skew: int) -> Tuple[Tuple[int, int], Tuple[int, int], Tuple[int, int], Tuple[int, int]]:
        return (
            (x + skew, y),
            (x + w + skew, y),
            (x + w, y + h),
            (x, y + h)
        )
    
    def _draw_skewed_rect(self, draw: ImageDraw.ImageDraw, x: int, y: int, w: int, h: int, skew: int, fill: Tuple[int, ...]):
        coords = self._skewed_rect_coords(x, y, w, h, skew)
        draw.polygon(coords, fill=fill)
    
    def _draw_health_bar(self, draw: ImageDraw.ImageDraw, x: int, display_hp: float, target_hp: float, is_left: bool = True):
        skew = -self.bar_skew if is_left else self.bar_skew
        
        self._draw_skewed_rect(draw, x, self.y_pos, self.bar_width, self.bar_height, skew, self.colors['bg'])
        
        damage_width = int(self.bar_width * (display_hp - target_hp) / 100)
        if damage_width > 0:
            bar_x = x if is_left else x + self.bar_width - damage_width
            self._draw_skewed_rect(draw, bar_x, self.y_pos, damage_width, self.bar_height, skew, self.colors['damage'])
        
        health_width = int(self.bar_width * target_hp / 100)
        if health_width > 0:
            bar_x = x if is_left else x + self.bar_width - health_width
            self._draw_skewed_rect(draw, bar_x, self.y_pos, health_width, self.bar_height, skew, self.colors['health'])
    
    def _draw_drive_gauge(self, draw: ImageDraw.ImageDraw, x: int, drive: int, is_left: bool = True):
        block_width = self.bar_width // 6
        block_height = 12
        gauge_y = self.y_pos + self.bar_height + 8
        
        for i in range(6):
            block_x = x + i * block_width if is_left else x + (5 - i) * block_width
            skew = -self.bar_skew if is_left else self.bar_skew
            
            color = self.colors['drive'] if i < drive else self.colors['drive_empty']
            self._draw_skewed_rect(draw, block_x, gauge_y, block_width - 4, block_height, skew, color)
    
    def _draw_player_info(self, draw: ImageDraw.ImageDraw, x: int, player_id: str, is_left: bool = True):
        info_y = self.y_pos + self.bar_height + 28
        
        try:
            font = ImageFont.truetype("Arial.ttf", 24)
        except:
            font = ImageFont.load_default()
        
        text_x = x if is_left else x + self.bar_width
        
        try:
            if is_left:
                draw.text((text_x, info_y), player_id, fill=self.colors['text'], font=font)
            else:
                bbox = draw.textbbox((0, 0), player_id, font=font)
                text_width = bbox[2] - bbox[0]
                draw.text((text_x - text_width, info_y), player_id, fill=self.colors['text'], font=font)
        except:
            if is_left:
                draw.text((text_x, info_y), player_id, fill=self.colors['text'])
            else:
                bbox = draw.textbbox((0, 0), player_id)
                text_width = bbox[2] - bbox[0]
                draw.text((text_x - text_width, info_y), player_id, fill=self.colors['text'])
    
    def render(self, frame: Optional[Image.Image] = None, p1_id: str = "P1", p2_id: str = "P2") -> Image.Image:
        if frame is None:
            frame = Image.new('RGBA', (self.width, self.height), (0, 0, 0, 0))
        elif frame.mode != 'RGBA':
            frame = frame.convert('RGBA')
        
        draw = ImageDraw.Draw(frame, 'RGBA')
        
        self._draw_health_bar(draw, self.p1_x, self.p1_hp_display, self.p1_hp_target, is_left=True)
        self._draw_health_bar(draw, self.p2_x, self.p2_hp_display, self.p2_hp_target, is_left=False)
        
        self._draw_drive_gauge(draw, self.p1_x, self.p1_drive, is_left=True)
        self._draw_drive_gauge(draw, self.p2_x, self.p2_drive, is_left=False)
        
        self._draw_player_info(draw, self.p1_x, p1_id, is_left=True)
        self._draw_player_info(draw, self.p2_x, p2_id, is_left=False)
        
        return frame
    
    def save_frame(self, output_path: str, frame: Optional[Image.Image] = None, p1_id: str = "P1", p2_id: str = "P2"):
        result = self.render(frame, p1_id, p2_id)
        if result.mode == 'RGBA':
            result = result.convert('RGB')
        result.save(output_path)
