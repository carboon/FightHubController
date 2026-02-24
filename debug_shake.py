from core.engine import FightStateEngine

engine = FightStateEngine(fps=60.0)
engine.add_event(0.5, 1, damage=10.0, is_super=True)

print("初始状态:")
print(f"  current_time = {engine.current_time}")
print(f"  current_shake = {engine.current_shake}")

for i in range(31):
    engine.update(engine.frame_time)

print(f"\n更新 31 帧后 (t = {engine.current_time}):")
print(f"  processed_event_indices = {engine.processed_event_indices}")
print(f"  current_shake = {engine.current_shake}")
print(f"  P1 HP: Display={engine.p1_hp_display:.1f}, Target={engine.p1_hp_target:.1f}")
print(f"  P2 HP: Display={engine.p2_hp_display:.1f}, Target={engine.p2_hp_target:.1f}")

for i in range(10):
    engine.update(engine.frame_time)

print(f"\n再更新 10 帧后 (t = {engine.current_time}):")
print(f"  current_shake = {engine.current_shake}")
