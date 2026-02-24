import streamlit as st
import numpy as np
from PIL import Image
import os
import time
import cv2

from core.engine import FightStateEngine
from core.renderer import SF6Renderer


def init_session_state():
    os.makedirs("videos", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("output", exist_ok=True)
    
    if 'engine' not in st.session_state:
        st.session_state.engine = FightStateEngine(fps=60.0)
    
    if 'renderer' not in st.session_state:
        st.session_state.renderer = SF6Renderer()
    
    if 'video_path' not in st.session_state:
        st.session_state.video_path = None
    
    if 'selected_video' not in st.session_state:
        st.session_state.selected_video = None
    
    if 'video_cap' not in st.session_state:
        st.session_state.video_cap = None
    
    if 'frame_cache' not in st.session_state:
        st.session_state.frame_cache = {}
    
    if 'video_width' not in st.session_state:
        st.session_state.video_width = 1920
    
    if 'video_height' not in st.session_state:
        st.session_state.video_height = 1080
    
    if 'video_fps' not in st.session_state:
        st.session_state.video_fps = 60.0
    
    if 'total_frames' not in st.session_state:
        st.session_state.total_frames = 0
    
    if 'current_frame' not in st.session_state:
        st.session_state.current_frame = 0
    
    if 'show_ui' not in st.session_state:
        st.session_state.show_ui = False
    
    if 'refresh_interval' not in st.session_state:
        st.session_state.refresh_interval = 0.5
    
    if 'is_playing' not in st.session_state:
        st.session_state.is_playing = False
    
    if 'playback_speed' not in st.session_state:
        st.session_state.playback_speed = 1.0
    
    if 'p1_id' not in st.session_state:
        st.session_state.p1_id = "P1"
    
    if 'p2_id' not in st.session_state:
        st.session_state.p2_id = "P2"


def get_cap():
    cv2.setNumThreads(0)  # 禁用 OpenCV 多线程
    
    # 每次都创建新的 cap，避免多线程竞争
    cap = cv2.VideoCapture(st.session_state.video_path)
    if not cap.isOpened():
        cap.release()
        return None
    
    return cap


def release_cap():
    if 'video_cap' in st.session_state and st.session_state.video_cap is not None:
        try:
            st.session_state.video_cap.release()
        except:
            pass
        st.session_state.video_cap = None


def get_video_frame(video_path: str, frame_idx: int):
    cache_key = f"{video_path}_{frame_idx}"
    
    if cache_key in st.session_state.frame_cache:
        return st.session_state.frame_cache[cache_key]
    
    cap = get_cap()
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    
    if ret:
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        st.session_state.frame_cache[cache_key] = rgb_frame
        
        if len(st.session_state.frame_cache) > 100:
            st.session_state.frame_cache.pop(next(iter(st.session_state.frame_cache)))
        
        return rgb_frame
    else:
        release_cap()
        return None


def preview_raw_frame() -> Image.Image:
    if not st.session_state.video_path:
        return Image.new('RGB', (1920, 1080), (20, 20, 20))
    
    frame_idx = st.session_state.current_frame
    video_frame = get_video_frame(st.session_state.video_path, frame_idx)
    
    if video_frame is not None:
        return Image.fromarray(video_frame)
    else:
        return Image.new('RGB', (1920, 1080), (20, 20, 20))


def render_preview_frame(time_pos: float) -> Image.Image:
    engine = st.session_state.engine
    renderer = st.session_state.renderer
    
    engine.seek_to(time_pos)
    
    state = engine.get_state()
    shake_offset = state['shake']
    
    renderer.set_hp(1, engine.p1_hp_target, engine.p1_hp_display)
    renderer.set_hp(2, engine.p2_hp_target, engine.p2_hp_display)
    renderer.set_drive(1, int(engine.p1_drive))
    renderer.set_drive(2, int(engine.p2_drive))
    
    if st.session_state.video_path:
        frame_idx = int(time_pos * st.session_state.video_fps)
        video_frame = get_video_frame(st.session_state.video_path, frame_idx)
        if video_frame is not None:
            frame = Image.fromarray(video_frame).convert('RGB')
        else:
            frame = Image.new('RGB', (1920, 1080), (20, 20, 20))
    
    result = renderer.render(frame, st.session_state.p1_id, st.session_state.p2_id, shake_offset)
    
    return result


def add_hit_event(player: int, damage: float, is_super: bool = False):
    engine = st.session_state.engine
    current_time = st.session_state.current_frame / st.session_state.video_fps
    
    engine.add_event(current_time, player, damage, is_super)
    save_match_json()
    st.toast(f"已添加事件: t={current_time:.2f}s, P{player} 攻击, 伤害={damage}", icon="✅")
    st.rerun()


def jump_to_event(event_idx: int):
    event = st.session_state.engine.hit_events[event_idx]
    frame_idx = int(event.timestamp * st.session_state.video_fps)
    st.session_state.current_frame = min(st.session_state.total_frames - 1, max(0, frame_idx))
    st.rerun()


def delete_event(event_idx: int):
    if 0 <= event_idx < len(st.session_state.engine.hit_events):
        event = st.session_state.engine.hit_events[event_idx]
        
        confirm_key = f"delete_confirm_{event_idx}"
        if not st.session_state.get(confirm_key, False):
            st.session_state[confirm_key] = True
            st.warning(f"⚠️ 确认删除事件 #{event_idx + 1}? t={event.timestamp:.2f}s")
            return
        
        del st.session_state.engine.hit_events[event_idx]
        save_match_json()
        st.toast("事件已删除", icon="🗑️")
        st.rerun()


def cancel_delete(event_idx: int):
    confirm_key = f"delete_confirm_{event_idx}"
    st.session_state[confirm_key] = False
    st.rerun()


def get_video_list() -> list[str]:
    videos_dir = "videos"
    if not os.path.exists(videos_dir):
        return []
    
    video_extensions = ['.mp4', '.avi', '.mov', '.mkv']
    video_files = []
    
    for filename in os.listdir(videos_dir):
        if any(filename.lower().endswith(ext) for ext in video_extensions):
            video_files.append(filename)
    
    return sorted(video_files)


def load_match_json(video_path: str):
    import json
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    json_path = f"data/{video_name}.json"
    
    if os.path.exists(json_path):
        try:
            from core.engine import HitEvent
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                st.session_state.engine.hit_events = []
                for event_data in data.get('hits', []):
                    event = HitEvent(
                        timestamp=event_data['timestamp'],
                        player=event_data['player'],
                        damage=event_data.get('damage', 10.0),
                        is_super=event_data.get('is_super', False)
                    )
                    st.session_state.engine.hit_events.append(event)
                st.success(f"已加载 {video_name}.json 的事件数据")
        except Exception as e:
            st.warning(f"加载 JSON 失败: {e}")


def save_match_json(video_path: str = None):
    import json
    import shutil
    
    if not video_path and st.session_state.video_path:
        video_path = st.session_state.video_path
    
    if not video_path:
        return
    
    video_name = os.path.splitext(os.path.basename(video_path))[0]
    json_path = f"data/{video_name}.json"
    
    if os.path.exists(json_path):
        backup_path = f"{json_path}.bak"
        try:
            shutil.copy2(json_path, backup_path)
        except Exception as e:
            pass
    
    events_data = {
        "hits": [
            {
                "timestamp": event.timestamp,
                "player": event.player,
                "damage": event.damage,
                "is_super": event.is_super
            }
            for event in st.session_state.engine.hit_events
        ]
    }
    
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(events_data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        pass


def load_video_info(video_path: str):
    try:
        cap = cv2.VideoCapture(video_path)
        fps = cap.get(cv2.CAP_PROP_FPS) or 60.0
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        cap.release()
        
        st.session_state.video_fps = fps
        st.session_state.total_frames = total_frames
        st.session_state.video_width = width
        st.session_state.video_height = height
        
        st.session_state.engine = FightStateEngine(fps=fps)
        
        if width != st.session_state.renderer.width or height != st.session_state.renderer.height:
            st.session_state.renderer = SF6Renderer(width=width, height=height)
        
        st.info(f"视频信息: FPS={fps:.2f}, 总帧数={total_frames}, 分辨率={width}x{height}")
        
    except Exception as e:
        st.error(f"读取视频信息失败: {e}")


def export_rendered_video():
    if not st.session_state.video_path or not st.session_state.engine.hit_events:
        st.error("请先上传视频并添加事件")
        return
    
    import json
    from moviepy.editor import VideoFileClip
    from tqdm import tqdm
    
    video_name = os.path.splitext(os.path.basename(st.session_state.video_path))[0]
    output_path = f"output/{video_name}_rendered.mp4"
    temp_path = "output/temp_render.mp4"
    
    os.makedirs("output", exist_ok=True)
    
    with st.spinner("正在渲染视频中...这可能需要几分钟"):
        engine = st.session_state.engine
        renderer = st.session_state.renderer
        
        engine.reset()
        
        cap = cv2.VideoCapture(st.session_state.video_path)
        total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        fps = cap.get(cv2.CAP_PROP_FPS)
        width = int(cap.get(cv2.CAP_PROP_FRAME_WIDTH))
        height = int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
        
        fourcc = cv2.VideoWriter_fourcc(*'mp4v')
        out = cv2.VideoWriter(temp_path, fourcc, fps, (width, height))
        
        progress_bar = st.progress(0)
        
        delta_time = 1.0 / fps
        
        for frame_idx in tqdm(range(total_frames), desc="渲染帧"):
            engine.update(delta_time)
            state = engine.get_state()
            shake_offset = state['shake']
            
            renderer.set_hp(1, engine.p1_hp_target, engine.p1_hp_display)
            renderer.set_hp(2, engine.p2_hp_target, engine.p2_hp_display)
            renderer.set_drive(1, int(engine.p1_drive))
            renderer.set_drive(2, int(engine.p2_drive))
            
            ret, frame = cap.read()
            
            if ret:
                video_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame_image = Image.fromarray(video_frame).convert('RGB')
            else:
                frame_image = Image.new('RGB', (width, height), (20, 20, 20))
            
            result = renderer.render(frame_image, st.session_state.p1_id, st.session_state.p2_id, shake_offset)
            
            if result.mode == 'RGBA':
                result = result.convert('RGB')
            
            result_frame = cv2.cvtColor(np.array(result), cv2.COLOR_RGB2BGR)
            out.write(result_frame)
            
            if frame_idx % 30 == 0:
                progress = frame_idx / total_frames
                progress_bar.progress(progress)
        
        cap.release()
        out.release()
        
        progress_bar.progress(0.9)
        
        try:
            original_video = VideoFileClip(st.session_state.video_path)
            audio = original_video.audio
            
            if audio is not None:
                rendered_video = VideoFileClip(temp_path)
                final_video = rendered_video.set_audio(audio)
                final_video.write_videofile(output_path, codec='libx264', audio_codec='aac')
                final_video.close()
                rendered_video.close()
            else:
                import shutil
                shutil.move(temp_path, output_path)
            
            original_video.close()
            
            if os.path.exists(temp_path):
                os.remove(temp_path)
        except Exception as e:
            st.warning(f"音频处理失败: {e}")
            import shutil
            shutil.move(temp_path, output_path)
        
        progress_bar.progress(1.0)
    
    st.success(f"视频渲染完成！保存路径: {output_path}")
    st.video(output_path)


# 主视频播放区域
def video_player_fragment():
    if st.session_state.video_path:
        col_btn_1, col_btn_2, col_btn_3, col_btn_4, col_btn_5, col_btn_6 = st.columns([1, 1, 1, 1, 1, 2])
        
        with col_btn_1:
            if st.button("⏮️ -10", use_container_width=True, key="main_btn_minus_10"):
                st.session_state.current_frame = max(0, st.session_state.current_frame - 10)
        
        with col_btn_2:
            if st.button("◀️ -1", use_container_width=True, key="main_btn_minus_1"):
                st.session_state.current_frame = max(0, st.session_state.current_frame - 1)
        
        with col_btn_3:
            st.session_state.is_playing = st.toggle("⏯️ 播放" if not st.session_state.is_playing else "⏸️ 暂停", 
                                                     value=st.session_state.is_playing, key="main_play_toggle")
        
        with col_btn_4:
            if st.button("+1 ▶️", use_container_width=True, key="main_btn_plus_1"):
                st.session_state.current_frame = min(st.session_state.total_frames - 1, st.session_state.current_frame + 1)
        
        with col_btn_5:
            if st.button("+10 ⏭️", use_container_width=True, key="main_btn_plus_10"):
                st.session_state.current_frame = min(st.session_state.total_frames - 1, st.session_state.current_frame + 10)
        
        with col_btn_6:
            st.session_state.playback_speed = st.selectbox("倍速", [0.25, 0.5, 1.0, 1.5, 2.0],
                                                          index=[0.25, 0.5, 1.0, 1.5, 2.0].index(st.session_state.playback_speed),
                                                          key="main_speed_select")
        
        new_frame = st.slider("帧位置", 0, max(0, st.session_state.total_frames - 1), 
                               st.session_state.current_frame, key="main_frame_slider")
        if new_frame != st.session_state.current_frame:
            st.session_state.current_frame = new_frame
            if st.session_state.is_playing:
                st.session_state.is_playing = False
        
        current_time = st.session_state.current_frame / st.session_state.video_fps
        st.write(f"⏱️ {current_time:.2f}s")
        
        st.session_state.show_ui = st.checkbox("显示 UI 叠加", value=st.session_state.show_ui, key="main_show_ui")
        
        # 计算显示宽度（原宽度的1/4）
        display_width = int(st.session_state.video_width / 4)
        
        # 然后再显示视频
        if st.session_state.is_playing and st.session_state.total_frames > 0:
            preview_img = preview_raw_frame()
            st.image(preview_img, width=display_width)
            
            refresh_interval = 1.0 / st.session_state.playback_speed
            st.caption(f"🔄 播放中... 帧: {st.session_state.current_frame}/{st.session_state.total_frames}")
            
            next_frame = st.session_state.current_frame + 1
            if next_frame >= st.session_state.total_frames:
                st.session_state.is_playing = False
            else:
                st.session_state.current_frame = next_frame
            
            time.sleep(refresh_interval)
            st.rerun()
        else:
            if st.session_state.show_ui:
                preview_img = render_preview_frame(st.session_state.current_frame / st.session_state.video_fps)
            else:
                preview_img = preview_raw_frame()
            st.image(preview_img, width=display_width)


def main():
    init_session_state()
    
    # CSS 样式：收紧布局
    st.markdown("""
    <style>
    .block-container {padding-top: 1rem; padding-bottom: 1rem;}
    .stButton > button {padding: 0.1rem 0.3rem; font-size: 0.85rem; min-height: 2rem; height: 2rem;}
    .stSelectbox > div > div {padding: 0.1rem 0.3rem; min-height: 2rem;}
    .stSlider {padding-top: 0.3rem; padding-bottom: 0.2rem;}
    .stCheckbox {margin-bottom: 0; padding-top: 0.2rem;}
    div[data-testid="stVerticalBlock"] {gap: 0.3rem;}
    [data-testid="stHorizontalBlock"] > div {gap: 0.3rem;}
    </style>
    """, unsafe_allow_html=True)
    
    st.set_page_config(
        page_title="AFH - AI Fight HUD",
        layout="wide",
        initial_sidebar_state="expanded"
    )
    
    st.title("🥊 AFH - AI Fight HUD")
    
    # 侧边栏
    with st.sidebar:
        st.header("📁 视频选择")
        
        video_list = get_video_list()
        
        if not video_list:
            st.info("📁 请将视频文件放入 `videos/` 目录")
            st.caption("支持格式: mp4, avi, mov, mkv")
        else:
            selected_video = st.selectbox(
                "选择视频",
                video_list,
                index=0 if 'selected_video' not in st.session_state else 
                       video_list.index(st.session_state.selected_video) 
                       if st.session_state.selected_video in video_list else 0,
                key="video_select"
            )
            
            if st.session_state.selected_video != selected_video:
                st.session_state.selected_video = selected_video
                video_path = f"videos/{selected_video}"
                st.session_state.video_path = video_path
                load_video_info(video_path)
                load_match_json(video_path)
                st.session_state.current_frame = 0
                st.rerun()
        
        st.divider()
        
        st.header("🎮 角色设置")
        st.session_state.p1_id = st.text_input("P1 角色名", value=st.session_state.p1_id, key="p1_name")
        st.session_state.p2_id = st.text_input("P2 角色名", value=st.session_state.p2_id, key="p2_name")
        
        st.divider()
        
        st.header("⚙️ 引擎设置")
        st.write(f"当前 FPS: {st.session_state.video_fps:.2f}")
        st.write(f"引擎 FPS: {st.session_state.engine.fps:.2f}")
        st.write(f"已添加事件数: {len(st.session_state.engine.hit_events)}")
        
        if st.button("重置引擎", key="reset_engine"):
            st.session_state.engine.reset()
            st.session_state.current_frame = 0
            st.session_state.frame_cache = {}
            release_cap()
            st.success("引擎和缓存已重置")
        
        st.caption(f"📊 缓存: {len(st.session_state.frame_cache)} 帧 | 句柄: {'已释放' if st.session_state.video_cap is None else '已连接'}")
        
        if st.button("🗑️ 清除缓存", key="clear_cache"):
            st.session_state.frame_cache = {}
            release_cap()
            st.toast("缓存和句柄已释放", icon="🗑️")
        
        st.divider()
        
        st.header("🚀 视频渲染")
        if st.button("开始最终渲染", type="primary", key="render_video"):
            export_rendered_video()
        
        if st.session_state.video_path:
            video_name = os.path.splitext(os.path.basename(st.session_state.video_path))[0]
            output_path = f"output/{video_name}_rendered.mp4"
            st.caption(f"📁 输出路径: {output_path}")
            
            if os.path.exists(output_path):
                file_size = os.path.getsize(output_path) / (1024 * 1024)
                st.caption(f"📊 已存在文件: {file_size:.2f} MB")
    
    # 主界面 - 视频播放器 fragment
    st.header("🎬 视频预览 & UI 叠加")
    video_player_fragment()
    
    # 打点工具 - 使用紧凑布局
    with st.expander("🎯 打点工具", expanded=True):
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("**🔴 P1 攻击 (对 P2)**")
            p1_damage = st.number_input("伤害", min_value=0.0, max_value=100.0, value=10.0, key="p1_damage")
            p1_is_super = st.checkbox("Super 技", key="p1_super_checkbox")
            
            if st.button(f"P1 攻击 -{p1_damage}", type="primary", use_container_width=True):
                add_hit_event(1, float(p1_damage), p1_is_super)
        
        with col2:
            st.markdown("**🔵 P2 攻击 (对 P1)**")
            p2_damage = st.number_input("伤害", min_value=0.0, max_value=100.0, value=10.0, key="p2_damage")
            p2_is_super = st.checkbox("Super 技", key="p2_super_checkbox")
            
            if st.button(f"P2 攻击 -{p2_damage}", type="primary", use_container_width=True):
                add_hit_event(2, float(p2_damage), p2_is_super)
        
        # 事件列表 - 可折叠
        with st.expander(f"📋 事件列表 ({len(st.session_state.engine.hit_events)}个)"):
            if st.session_state.engine.hit_events:
                for i, event in enumerate(reversed(st.session_state.engine.hit_events)):
                    event_idx = len(st.session_state.engine.hit_events) - 1 - i
                    player_color = "🔴" if event.player == 1 else "🔵"
                    super_mark = " ⭐" if event.is_super else ""
                    confirm_key = f"delete_confirm_{event_idx}"
                    is_confirming = st.session_state.get(confirm_key, False)
                    
                    col_event, col_jump, col_delete = st.columns([3, 1, 1])
                    
                    with col_event:
                        if is_confirming:
                            st.error(f"⚠️ 确认删除? t={event.timestamp:.2f}s")
                        else:
                            st.write(f"{player_color} #{event_idx + 1}: t={event.timestamp:.2f}s{super_mark}")
                    
                    with col_jump:
                        if st.button("跳转", key=f"jump_{event_idx}"):
                            jump_to_event(event_idx)
                    
                    with col_delete:
                        if is_confirming:
                            col_yes, col_no = st.columns(2)
                            with col_yes:
                                if st.button("✅", key=f"confirm_yes_{event_idx}"):
                                    delete_event(event_idx)
                            with col_no:
                                if st.button("❌", key=f"confirm_no_{event_idx}"):
                                    cancel_delete(event_idx)
                        else:
                            if st.button("🗑️", key=f"delete_btn_{event_idx}"):
                                delete_event(event_idx)
            else:
                st.caption("暂无事件")


if __name__ == "__main__":
    main()

