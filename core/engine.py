import json
import random
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass


@dataclass
class HitEvent:
    timestamp: float
    player: int
    damage: float
    is_super: bool = False


class FightStateEngine:
    
    def __init__(self, fps: float = 60.0):
        self.fps = fps
        self.frame_time = 1.0 / fps
        
        self.current_time = 0.0
        self.prev_time = 0.0
        self.hit_events: List[HitEvent] = []
        self.processed_event_indices = set()
        
        self.p1_hp_target = 100.0
        self.p1_hp_display = 100.0
        self.p2_hp_target = 100.0
        self.p2_hp_display = 100.0
        
        self.hp_decay = 0.1
        self.hit_delay = 0.15
        
        self.shake_intensity = 3.0
        self.shake_decay = 0.8
        self.current_shake = 0.0
        
        self.p1_drive = 6
        self.p2_drive = 6
        self.drive_regen_rate = 0.5
        
        self.p1_last_hit_time = 0.0
        self.p2_last_hit_time = 0.0
        self.hit_player = None
    
    def load_events_from_json(self, json_path: str):
        with open(json_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for event in data.get('hits', []):
                self.hit_events.append(HitEvent(
                    timestamp=event['timestamp'],
                    player=event['player'],
                    damage=event.get('damage', 10.0),
                    is_super=event.get('is_super', False)
                ))
        self.hit_events.sort(key=lambda e: e.timestamp)
    
    def add_event(self, timestamp: float, player: int, damage: float, is_super: bool = False):
        self.hit_events.append(HitEvent(timestamp, player, damage, is_super))
        self.hit_events.sort(key=lambda e: e.timestamp)
    
    def _apply_hit(self, event: HitEvent):
        target_player = 2 if event.player == 1 else 1
        if target_player == 1:
            self.p1_hp_target = max(0, self.p1_hp_target - event.damage)
            self.p1_last_hit_time = self.current_time
        else:
            self.p2_hp_target = max(0, self.p2_hp_target - event.damage)
            self.p2_last_hit_time = self.current_time
        
        self.current_shake = self.shake_intensity * (2.0 if event.is_super else 1.0)
        self.hit_player = target_player
    
    def _smooth_chase(self, display_hp: float, target_hp: float, last_hit_time: float) -> float:
        if display_hp <= target_hp:
            return target_hp
        
        diff = display_hp - target_hp
        
        if self.current_time < last_hit_time + self.hit_delay:
            return display_hp
        
        return display_hp * (1 - self.hp_decay) + target_hp * self.hp_decay
    
    def update(self, delta_time: float):
        self.prev_time = self.current_time
        self.current_time += delta_time
        
        for i, event in enumerate(self.hit_events):
            if i not in self.processed_event_indices and self.prev_time < event.timestamp <= self.current_time + 1e-6:
                self._apply_hit(event)
                self.processed_event_indices.add(i)
        
        self.p1_hp_display = self._smooth_chase(self.p1_hp_display, self.p1_hp_target, self.p1_last_hit_time)
        self.p2_hp_display = self._smooth_chase(self.p2_hp_display, self.p2_hp_target, self.p2_last_hit_time)
        
        self.current_shake *= self.shake_decay
        if self.current_shake < 0.1:
            self.current_shake = 0.0
        
        drive_regen = self.drive_regen_rate * delta_time
        self.p1_drive = min(6.0, self.p1_drive + drive_regen)
        self.p2_drive = min(6.0, self.p2_drive + drive_regen)
    
    def get_shake_offset(self) -> Tuple[int, int]:
        if self.current_shake < 0.1:
            return (0, 0)
        
        offset_x = random.uniform(-1, 1) * self.current_shake
        offset_y = random.uniform(-1, 1) * self.current_shake
        
        return (int(offset_x), int(offset_y))
    
    def get_state(self) -> Dict:
        return {
            'p1': {
                'hp_target': self.p1_hp_target,
                'hp_display': self.p1_hp_display,
                'drive': self.p1_drive
            },
            'p2': {
                'hp_target': self.p2_hp_target,
                'hp_display': self.p2_hp_display,
                'drive': self.p2_drive
            },
            'shake': self.get_shake_offset(),
            'time': self.current_time
        }
    
    def reset(self):
        self.current_time = 0.0
        self.prev_time = 0.0
        self.processed_event_indices.clear()
        self.p1_hp_target = 100.0
        self.p1_hp_display = 100.0
        self.p2_hp_target = 100.0
        self.p2_hp_display = 100.0
        self.p1_drive = 6
        self.p2_drive = 6
        self.current_shake = 0.0
        self.p1_last_hit_time = 0.0
        self.p2_last_hit_time = 0.0
        self.hit_player = None
    
    def seek_to(self, time: float):
        self.reset()
        self.current_time = time
        
        for i, event in enumerate(self.hit_events):
            if event.timestamp <= time:
                self._apply_hit(event)
                self.processed_event_indices.add(i)
        
        self.p1_hp_display = self.p1_hp_target
        self.p2_hp_display = self.p2_hp_target
        self.current_shake = 0.0
