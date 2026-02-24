from core.renderer import SF6Renderer

def test_static_render():
    renderer = SF6Renderer()
    
    renderer.set_hp(1, 75, 90)
    renderer.set_hp(2, 60, 80)
    
    renderer.set_drive(1, 4)
    renderer.set_drive(2, 2)
    
    output_path = "/Volumes/DATA/FightHubController/output/test_static_render.png"
    renderer.save_frame(output_path, p1_id="RYU", p2_id="KEN")
    
    print(f"Test render saved to: {output_path}")
    print("P1 HP: Display={renderer.p1_hp_display}%, Target={renderer.p1_hp_target}%")
    print("P2 HP: Display={renderer.p2_hp_display}%, Target={renderer.p2_hp_target}%")
    print("P1 Drive: {renderer.p1_drive}/6")
    print("P2 Drive: {renderer.p2_drive}/6")

if __name__ == "__main__":
    test_static_render()
