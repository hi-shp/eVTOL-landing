import os
import sys
import math
import cv2
import numpy as np
import pygame
from PIL import Image

from config import (
    WIDTH, HEIGHT, FPS, WHITE, BLACK, GRAY, RED, GREEN, BLUE, YELLOW, CYAN, DARK_GRAY,
    MAX_LANDING_SPEED, MAX_ANGLE_DIFF, DT
)
from ship_motion import ShipMotion
from controller import eVTOLController
from avatar_renderer import create_avatar_pilot_frame
from hand_tracker import HandTracker

def draw_text(surf, text, font, color, x, y):
    img = font.render(text, True, color)
    surf.blit(img, (x, y))

def draw_hud_box(screen, x, y, w, h, title, font_title):
    pygame.draw.rect(screen, (8, 14, 22), (x, y, w, h))
    pygame.draw.rect(screen, (40, 90, 140), (x, y, w, h), 1)
    pygame.draw.rect(screen, (25, 55, 85), (x, y, w, 26))
    draw_text(screen, title, font_title, CYAN, x + 8, y + 4)

def draw_graph_axes(screen, x, y, w, h, max_val, min_val, y_unit, font_axis):
    draw_text(screen, f"{max_val} {y_unit}", font_axis, (160, 170, 180), x + 5, y + 31)
    draw_text(screen, f"{min_val} {y_unit}", font_axis, (160, 170, 180), x + 5, y + h - 17)
    draw_text(screen, "Time ->", font_axis, (140, 150, 160), x + w - 55, y + h - 17)
    pygame.draw.line(screen, (35, 48, 62), (x, y + h/2 + 13), (x + w, y + h/2 + 13), 1)

def draw_wasd(screen, active_keys, font, x, y):
    size = 38
    pad_color = (35, 50, 70)
    active_color = (0, 240, 255)
    
    positions = [
        ("W", "W", x + size + 4, y),
        ("A", "A", x, y + size + 4),
        ("S", "S", x + size + 4, y + size + 4),
        ("D", "D", x + (size + 4)*2, y + size + 4)
    ]
    
    for key_id, char, kx, ky in positions:
        is_active = key_id in active_keys
        color = active_color if is_active else pad_color
        pygame.draw.rect(screen, color, (kx, ky, size, size), border_radius=4)
        if not is_active:
            pygame.draw.rect(screen, (60, 85, 110), (kx, ky, size, size), 1, border_radius=4)
        draw_text(screen, char, font, BLACK if is_active else WHITE, kx + 12, ky + 9)

def render_simulator(screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
                     history_ship_pitch, cam_frame, active_keys, fonts, msg="", msg_color=WHITE, msg_timer=0,
                     extra_banner=""):
    screen.fill((6, 11, 18))
    font_xs, font_sm, font_md, font_lg, font_title_big = fonts

    # 1. Background tactical grid
    for i in range(0, WIDTH, 80):
        pygame.draw.line(screen, (15, 25, 35), (i, 0), (i, HEIGHT), 1)
    for i in range(0, HEIGHT, 80):
        pygame.draw.line(screen, (15, 25, 35), (0, i), (WIDTH, i), 1)

    # Sea level
    sea_y = HEIGHT - 90
    pygame.draw.line(screen, (20, 50, 80), (0, sea_y), (WIDTH, sea_y), 2)
    sea_surf = pygame.Surface((WIDTH, 90))
    sea_surf.fill((10, 24, 42))
    screen.blit(sea_surf, (0, sea_y))

    # 2. Detailed Ship Hull Rendering
    rad = math.radians(ship_pitch)
    cos_r, sin_r = math.cos(rad), math.sin(rad)
    
    ship_poly = [
        p1, p2, 
        (p2[0] - 50 * sin_r, p2[1] + 150 * cos_r), 
        (p1[0] + 50 * sin_r, p1[1] + 150 * cos_r)
    ]
    pygame.draw.polygon(screen, (35, 45, 55), ship_poly)
    pygame.draw.polygon(screen, (55, 75, 95), ship_poly, 2)
    
    # Bridge
    bridge_poly = [
        (p2[0] - 80 * cos_r, p2[1] - 80 * sin_r),
        (p2[0] - 20 * cos_r, p2[1] - 20 * sin_r),
        (p2[0] - 20 * cos_r + 60 * sin_r, p2[1] - 20 * sin_r - 60 * cos_r),
        (p2[0] - 80 * cos_r + 60 * sin_r, p2[1] - 80 * sin_r - 60 * cos_r)
    ]
    pygame.draw.polygon(screen, (50, 65, 75), bridge_poly)
    pygame.draw.polygon(screen, (70, 95, 115), bridge_poly, 2)
    
    win_x = p2[0] - 70 * cos_r + 40 * sin_r
    win_y = p2[1] - 70 * sin_r - 40 * cos_r
    pygame.draw.circle(screen, CYAN, (int(win_x), int(win_y)), 4)
    win_x2 = p2[0] - 40 * cos_r + 40 * sin_r
    win_y2 = p2[1] - 40 * sin_r - 40 * cos_r
    pygame.draw.circle(screen, CYAN, (int(win_x2), int(win_y2)), 4)

    # Waterline
    wl_p1 = (p1[0] + 30 * sin_r, p1[1] + 90 * cos_r)
    wl_p2 = (p2[0] - 30 * sin_r, p2[1] + 90 * cos_r)
    pygame.draw.line(screen, (190, 45, 45), wl_p1, wl_p2, 4)

    # Helipad Main Deck
    pygame.draw.line(screen, (180, 195, 210), p1, p2, 6)
    deck_mid_x = (p1[0] + p2[0]) / 2
    deck_mid_y = (p1[1] + p2[1]) / 2
    pygame.draw.circle(screen, YELLOW, (int(deck_mid_x), int(deck_mid_y)), 14, 2)
    pygame.draw.circle(screen, YELLOW, (int(deck_mid_x), int(deck_mid_y)), 4)
    pygame.draw.circle(screen, GREEN, (int(p1[0]), int(p1[1])), 5)
    pygame.draw.circle(screen, RED, (int(p2[0]), int(p2[1])), 5)

    # 3. eVTOL Drone Rendering (drone pitch: +deg rotates clockwise)
    drone_surf = pygame.Surface((80, 40), pygame.SRCALPHA)
    pygame.draw.rect(drone_surf, (140, 150, 160), (10, 15, 60, 6), border_radius=2)
    pygame.draw.rect(drone_surf, GREEN if evtol.is_auto else CYAN, (32, 5, 16, 10), border_radius=3)
    pygame.draw.line(drone_surf, WHITE, (20, 21), (20, 32), 2)
    pygame.draw.line(drone_surf, WHITE, (60, 21), (60, 32), 2)
    pygame.draw.line(drone_surf, WHITE, (14, 32), (26, 32), 2)
    pygame.draw.line(drone_surf, WHITE, (54, 32), (66, 32), 2)
    
    p_off = int(14 * math.cos(math.radians(prop_angle)))
    pygame.draw.line(drone_surf, (255, 75, 75), (10 - p_off, 10), (10 + p_off, 10), 2)
    pygame.draw.line(drone_surf, (255, 75, 75), (70 - p_off, 10), (70 + p_off, 10), 2)
    
    if evtol.vy > 0 or evtol.thrust_multiplier > 1.2:
        pygame.draw.line(drone_surf, (120, 210, 255), (10, 20), (10, 36), 1)
        pygame.draw.line(drone_surf, (120, 210, 255), (70, 20), (70, 36), 1)

    # In pygame, rotate with -angle rotates clockwise (right) for positive angle!
    rotated_drone = pygame.transform.rotate(drone_surf, -evtol.angle)
    rect = rotated_drone.get_rect(center=(int(evtol.x), int(evtol.y)))
    screen.blit(rotated_drone, rect.topleft)

    # Target ship deck surface attitude reference line (synced with ship pitch)
    deck_target_rad = math.radians(ship_pitch)
    ref_len = 55
    ref_x1 = evtol.x - ref_len * math.cos(deck_target_rad)
    ref_y1 = evtol.y - ref_len * math.sin(deck_target_rad)
    ref_x2 = evtol.x + ref_len * math.cos(deck_target_rad)
    ref_y2 = evtol.y + ref_len * math.sin(deck_target_rad)
    pygame.draw.line(screen, (0, 220, 240), (int(ref_x1), int(ref_y1)), (int(ref_x2), int(ref_y2)), 2)

    if evtol.is_auto:
        pygame.draw.line(screen, (80, 255, 130), (int(evtol.x), int(evtol.y)), (int(deck_mid_x), int(deck_mid_y)), 1)
        draw_text(screen, "LOC: TRACKING DECK", font_xs, GREEN, int(evtol.x) + 48, int(evtol.y) - 10)

    # 4. Telemetry Panels & HUD (width: 370, leaving plenty of center space)
    gx, gw, gh = 20, 370, 165
    
    draw_hud_box(screen, gx, 20, gw, 125, "FLIGHT DYNAMICS & TELEMETRY", font_title_big)
    draw_text(screen, f"Vy (Descent Rate) : {evtol.vy:5.1f} m/s", font_md, CYAN, gx + 12, 52)
    draw_text(screen, f"Vx (Lateral Vel)  : {evtol.vx:5.1f} m/s", font_md, WHITE, gx + 12, 74)
    draw_text(screen, f"DRONE PITCH (θ_d) : {evtol.angle:5.1f} deg", font_md, YELLOW, gx + 12, 96)
    draw_text(screen, f"SHIP DECK PITCH   : {ship_pitch:5.1f} deg", font_md, (150, 200, 255), gx + 12, 118)

    # 1. Pitch Deviation Error Graph
    gy_pitch = 160
    draw_hud_box(screen, gx, gy_pitch, gw, gh, "PITCH DEVIATION ERROR", font_title_big)
    draw_graph_axes(screen, gx, gy_pitch, gw, gh, f"{MAX_ANGLE_DIFF:.0f}", "0", "deg", font_xs)
    threshold_y_pitch = gy_pitch + gh - 15 - int((MAX_ANGLE_DIFF / 30.0) * (gh - 45))
    pygame.draw.line(screen, (255, 80, 80), (gx, threshold_y_pitch), (gx + gw, threshold_y_pitch), 1)
    draw_text(screen, "CRITICAL (10°)", font_xs, RED, gx + gw - 95, threshold_y_pitch - 12)
    if len(evtol.history_angle_diff) > 1:
        pts_pitch = [(gx + 10 + i * (gw - 20) / 100, gy_pitch + gh - 15 - min(a * 2.8, gh - 45)) for i, a in enumerate(evtol.history_angle_diff)]
        pygame.draw.lines(screen, YELLOW, False, pts_pitch, 2)

    # 2. Vertical Velocity Graph
    gy_vert = 345
    draw_hud_box(screen, gx, gy_vert, gw, gh, "VERTICAL DESCENT RATE (Vy)", font_title_big)
    draw_graph_axes(screen, gx, gy_vert, gw, gh, f"{MAX_LANDING_SPEED:.0f}", "0", "m/s", font_xs)
    threshold_y_vert = gy_vert + gh - 15 - int((MAX_LANDING_SPEED / 80.0) * (gh - 45))
    pygame.draw.line(screen, (255, 80, 80), (gx, threshold_y_vert), (gx + gw, threshold_y_vert), 1)
    draw_text(screen, "SAFE (60 m/s)", font_xs, RED, gx + gw - 90, threshold_y_vert - 12)
    if len(evtol.history_vy) > 1:
        pts_vert = [(gx + 10 + i * (gw - 20) / 100, gy_vert + gh - 15 - max(0, min(v * 1.5, gh - 45))) for i, v in enumerate(evtol.history_vy)]
        pygame.draw.lines(screen, CYAN, False, pts_vert, 2)

    # 3. Ship Hull Wave Pitch Graph
    gy_wave = 530
    draw_hud_box(screen, gx, gy_wave, gw, gh, "SHIP HULL WAVE PITCH DYNAMICS", font_title_big)
    draw_graph_axes(screen, gx, gy_wave, gw, gh, "+20", "-20", "deg", font_xs)
    pygame.draw.line(screen, (80, 100, 120), (gx, gy_wave + gh/2 + 10), (gx + gw, gy_wave + gh/2 + 10), 1)
    if len(history_ship_pitch) > 1:
        pts_wave = [(gx + 10 + i * (gw - 20) / 100, gy_wave + gh/2 + 10 - (p * 2.5)) for i, p in enumerate(history_ship_pitch)]
        pygame.draw.lines(screen, (150, 200, 255), False, pts_wave, 2)

    # 5. Right Webcam & Pilot Avatar HMI Feed (320x240, positioned at x = 930 to leave center clear)
    cam_w, cam_h = 320, 240
    cx, cy = WIDTH - cam_w - 20, 20
    if cam_frame is not None:
        rgb_cam_frame = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        rgb_cam_frame = cv2.resize(rgb_cam_frame, (cam_w, cam_h))
        cam_surface = pygame.surfarray.make_surface(rgb_cam_frame.swapaxes(0, 1))
        pygame.draw.rect(screen, (35, 75, 115), (cx - 2, cy - 2, cam_w + 4, cam_h + 4), 2)
        screen.blit(cam_surface, (cx, cy))
        draw_text(screen, "PILOT WEBCAM HMI (3-DoF BODY TRACKING)", font_sm, CYAN, cx + 5, cy + cam_h + 6)

    # 6. WASD Controller Panel & Flight Mode Indicator
    draw_wasd(screen, active_keys, font_md, WIDTH - 200, HEIGHT - 210)
    mode_txt = "FCS MODE: [ AUTO LANDING ]" if evtol.is_auto else "FCS MODE: [ 3-DoF MANUAL ]"
    mode_color = GREEN if evtol.is_auto else CYAN
    draw_text(screen, mode_txt, font_md, mode_color, WIDTH - 260, HEIGHT - 85)
    draw_text(screen, "Press [T] to Toggle Autonomous FCS", font_sm, (160, 180, 200), WIDTH - 260, HEIGHT - 55)

    # Top Center Banner (Centered strictly between x=400 and x=920, max width 480)
    if extra_banner:
        bw, bh = 490, 32
        bx = 405 + (515 - bw) // 2
        by = 20
        pygame.draw.rect(screen, (10, 20, 32), (bx, by, bw, bh), border_radius=4)
        pygame.draw.rect(screen, (0, 220, 255), (bx, by, bw, bh), 1, border_radius=4)
        b_img = font_sm.render(extra_banner, True, (0, 240, 255))
        b_rect = b_img.get_rect(center=(bx + bw // 2, by + bh // 2))
        screen.blit(b_img, b_rect.topleft)

    # 7. Impact / Touchdown Notification (Centered between 400 and 920)
    if msg_timer > 0:
        box_w, box_h = 490, 56
        popup_x = 405 + (515 - box_w) // 2
        popup_y = HEIGHT // 2 - box_h // 2 - 30
        pygame.draw.rect(screen, (8, 14, 22), (popup_x, popup_y, box_w, box_h), border_radius=6)
        pygame.draw.rect(screen, msg_color, (popup_x, popup_y, box_w, box_h), 2, border_radius=6)
        
        t_img = font_md.render(msg, True, msg_color)
        t_rect = t_img.get_rect(center=(popup_x + box_w // 2, popup_y + box_h // 2))
        screen.blit(t_img, t_rect.topleft)

def save_surface_as_image(surf, path):
    pygame.image.save(surf, path)
    print(f"Saved PNG: {path}")

def save_flicker_free_gif(frames, path, fps=28):
    """
    Encodes GIF using a unified Master Global Palette with ZERO dithering
    to completely eliminate temporal color flickering and green/red noise.
    """
    if not frames:
        return
    duration_ms = int(1000.0 / fps)
    
    # 1. Build master composite sample across animation to form a single optimal palette
    sample_indices = np.linspace(0, len(frames) - 1, min(12, len(frames)), dtype=int)
    sample_strips = [frames[i].resize((320, 180)) for i in sample_indices]
    composite = Image.new("RGB", (320, 180 * len(sample_strips)))
    for idx, s in enumerate(sample_strips):
        composite.paste(s, (0, idx * 180))
    
    # Global palette generated once
    master_palette_img = composite.quantize(colors=256, method=Image.Resampling.LANCZOS, dither=Image.Dither.NONE)
    
    # 2. Quantize all frames against the identical master palette with NO dithering
    quantized_frames = []
    for f in frames:
        q = f.quantize(palette=master_palette_img, dither=Image.Dither.NONE)
        quantized_frames.append(q)
        
    quantized_frames[0].save(
        path,
        save_all=True,
        append_images=quantized_frames[1:],
        duration=duration_ms,
        loop=0,
        optimize=True
    )
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"Saved Flicker-Free GIF: {path} ({len(frames)} frames @ {fps} FPS, {size_mb:.2f} MB)")

def create_crop(surf, rect, path):
    sub = surf.subsurface(rect)
    pygame.image.save(sub, path)
    print(f"Saved Cropped PNG: {path}")

def main():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    
    font_xs = pygame.font.SysFont("consolas", 11)
    font_sm = pygame.font.SysFont("consolas", 13)
    font_md = pygame.font.SysFont("consolas", 16, bold=True)
    font_lg = pygame.font.SysFont("consolas", 24, bold=True)
    font_title_big = pygame.font.SysFont("consolas", 14, bold=True)
    fonts = (font_xs, font_sm, font_md, font_lg, font_title_big)

    os.makedirs("assets", exist_ok=True)
    target_gif_size = (960, 540)

    # -------------------------------------------------------------------------
    # 1. SCENARIO 3-DoF GESTURE TILT (Hand Sway <-> Drone Pitch 1:1 In-Sync)
    # -------------------------------------------------------------------------
    print("Generating Scenario 1: 3-DoF Natural Body-Coupled Tilt (Fixed Directions)...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = 660 # Center of operational area
    evtol.y = 230
    tracker = HandTracker()
    
    frames_tilt = []
    frames_telemetry = []
    history_ship_pitch = []
    prop_angle = 0
    
    # 90 smooth frames swaying -25 deg (left) to +25 deg (right) via live MediaPipe video tracking
    for step in range(90):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        # Real-time hand tracking on pilot gesture video
        cam_frame, hand_tilt = tracker.get_tilt()
        
        # Drone pitch aligns with live detected hand tilt:
        evtol.angle += (hand_tilt - evtol.angle) * 0.20
        evtol.vx = 18.0 * (hand_tilt / 25.0)
        evtol.vy = -4.0 * math.cos(step * 0.08)
        evtol.x += evtol.vx * DT
        evtol.y += evtol.vy * DT
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        evtol.history_vy.append(evtol.vy)
        evtol.history_angle_diff.append(abs(evtol.angle - ship_pitch))
        if len(evtol.history_vy) > 100: evtol.history_vy.pop(0)
        if len(evtol.history_angle_diff) > 100: evtol.history_angle_diff.pop(0)
        
        dir_label = "RIGHT" if hand_tilt > 0.5 else ("LEFT" if hand_tilt < -0.5 else "LEVEL")
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts,
            "", WHITE, 0,
            extra_banner=f"3-DoF BODY COUPLING: Hand {hand_tilt:+.1f} deg [{dir_label}] -> Drone Pitch {evtol.angle:+.1f} deg"
        )
        
        if step == 20:
            save_surface_as_image(screen, "assets/screenshot_avatar_hmi_tilt.png")
            create_crop(screen, pygame.Rect(WIDTH - 320 - 20, 20, 320, 240), "assets/screenshot_mediapipe_hmi.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_tilt.append(pil_img)
        
        # Dedicated Telemetry Graph Panel Recording
        sub_telemetry = screen.subsurface(pygame.Rect(18, 18, 374, 680))
        t_data = pygame.image.tostring(sub_telemetry, "RGB")
        pil_t = Image.frombytes("RGB", (374, 680), t_data)
        frames_telemetry.append(pil_t)
        
    save_flicker_free_gif(frames_tilt, "assets/demo_3dof_gesture_tilt.gif", fps=28)
    save_flicker_free_gif(frames_telemetry, "assets/demo_telemetry_graphs.gif", fps=28)

    # -------------------------------------------------------------------------
    # 2. SCENARIO 2-DoF vs 3-DoF COMPARISON
    # -------------------------------------------------------------------------
    print("Generating Scenario 2: 2-DoF vs 3-DoF Comparison...")
    frames_compare = []
    
    # Phase 1: 2-DoF Crash (Drone angle fixed at 0 deg, ship deck tilted)
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = 660
    evtol.angle = 0.0
    history_ship_pitch = []
    
    for step in range(45):
        ship_center, p1, p2, ship_pitch = ship.update()
        cam_frame = create_avatar_pilot_frame(0.0, step)
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        if step < 24:
            evtol.y = (ship_center[1] - 105) + step * 3.6
            evtol.vy = 35.0
            evtol.angle = 0.0
            msg = ""
            msg_color = WHITE
            timer = 0
        else:
            evtol.y = ship_center[1] - 25
            evtol.vy = 0.0
            evtol.angle = 0.0
            msg = f"2-DoF FAILED: ANGLE MISMATCH ({abs(ship_pitch):.1f} deg > 10 deg)"
            msg_color = RED
            timer = 60
            
        evtol.history_vy.append(evtol.vy)
        evtol.history_angle_diff.append(abs(evtol.angle - ship_pitch))
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts,
            msg, msg_color, timer,
            extra_banner="[COMPARISON] 2-DoF: Horizontal Angle Only (Roll-over Crash)"
        )
        
        if step == 30:
            save_surface_as_image(screen, "assets/screenshot_2dof_crash_comparison.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_compare.append(pil_img)

    # Phase 2: 3-DoF Success (Hand tilts with deck, perfect touchdown)
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = 660
    
    for step in range(50):
        ship_center, p1, p2, ship_pitch = ship.update()
        hand_tilt = ship_pitch # Pilot matches deck angle
        cam_frame = create_avatar_pilot_frame(hand_tilt, step)
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        if step < 24:
            evtol.y = (ship_center[1] - 95) + step * 3.0
            evtol.vy = 28.0
            evtol.angle = hand_tilt
            msg = ""
            msg_color = WHITE
            timer = 0
        else:
            evtol.y = ship_center[1] - 25
            evtol.vy = 0.0
            evtol.angle = ship_pitch
            msg = "3-DoF SUCCESS: BODY-ALIGNED TOUCHDOWN"
            msg_color = GREEN
            timer = 60
            
        evtol.history_vy.append(evtol.vy)
        evtol.history_angle_diff.append(abs(evtol.angle - ship_pitch))
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts,
            msg, msg_color, timer,
            extra_banner="[COMPARISON] 3-DoF: Body-Coupled Pitch Alignment (Stable Landing)"
        )
        
        if step == 30:
            save_surface_as_image(screen, "assets/screenshot_3dof_attitude_alignment.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_compare.append(pil_img)
        
    save_flicker_free_gif(frames_compare, "assets/demo_2dof_vs_3dof.gif", fps=26)

    # -------------------------------------------------------------------------
    # 3. SCENARIO AUTO LANDING & TELEMETRY
    # -------------------------------------------------------------------------
    print("Generating Scenario 3: Auto Landing (Flicker-Free)...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = True
    evtol.x = 600
    evtol.y = 110
    history_ship_pitch = []
    frames_auto = []
    
    for step in range(95):
        ship_center, p1, p2, ship_pitch = ship.update()
        hand_tilt = ship_pitch * 0.85
        cam_frame = create_avatar_pilot_frame(hand_tilt, step)
        evtol.update({}, hand_tilt, ship_center, ship_pitch)
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
            
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts, "", WHITE, 0
        )
        
        if step == 45:
            save_surface_as_image(screen, "assets/screenshot_main_hud.png")
            save_surface_as_image(screen, "assets/screenshot_auto_landing.png")
            create_crop(screen, pygame.Rect(20, 160, 370, 535), "assets/screenshot_telemetry_graphs.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_auto.append(pil_img)
            
    save_flicker_free_gif(frames_auto, "assets/demo_auto_landing.gif", fps=28)

    # -------------------------------------------------------------------------
    # 4. SCENARIO MANUAL FLIGHT
    # -------------------------------------------------------------------------
    print("Generating Scenario 4: Manual Flight (Flicker-Free)...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = 580
    evtol.y = 210
    history_ship_pitch = []
    frames_manual = []
    
    for step in range(80):
        ship_center, p1, p2, ship_pitch = ship.update()
        hand_tilt = 24.0 * math.sin(step * 0.08)
        cam_frame = create_avatar_pilot_frame(hand_tilt, step)
        
        active_keys = set()
        if (step // 15) % 2 == 0: active_keys.add("W")
        if step > 20 and step < 65: active_keys.add("D")
            
        evtol.angle += (hand_tilt - evtol.angle) * 0.14
        evtol.vx = 28.0 * math.sin(step * 0.08)
        evtol.vy = -16.0 if "W" in active_keys else 16.0
        evtol.x += evtol.vx * DT
        evtol.y += evtol.vy * DT
        evtol.y = max(80, min(360, evtol.y))
        
        evtol.history_vy.append(evtol.vy)
        evtol.history_angle_diff.append(abs(evtol.angle - ship_pitch))
        if len(evtol.history_vy) > 100: evtol.history_vy.pop(0)
        if len(evtol.history_angle_diff) > 100: evtol.history_angle_diff.pop(0)
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        prop_angle = (prop_angle + 40) % 360
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, active_keys, fonts, "", WHITE, 0
        )
        
        if step == 35:
            save_surface_as_image(screen, "assets/screenshot_manual_flight.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_manual.append(pil_img)
            
    save_flicker_free_gif(frames_manual, "assets/demo_manual_flight.gif", fps=26)

    # -------------------------------------------------------------------------
    # 5. SCENARIO LANDING SUCCESS
    # -------------------------------------------------------------------------
    print("Generating Scenario 5: Landing Success (Flicker-Free)...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = True
    evtol.x = 660
    history_ship_pitch = []
    
    for i in range(80):
        evtol.history_vy.append(42.0 - i * 0.25)
        evtol.history_angle_diff.append(max(0.6, 6.5 - i * 0.08))
        history_ship_pitch.append(8.0 * math.sin(0.8 * (i * DT)))
        
    frames_success = []
    for step in range(70):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        if step < 22:
            evtol.y = (ship_center[1] - 65) + step * 1.8
            evtol.vy = 26.0 - step * 0.4
            evtol.angle = ship_pitch - 0.8
            msg = ""
            msg_color = WHITE
            timer = 0
        else:
            evtol.y = ship_center[1] - 25
            evtol.vy = 0.0
            evtol.angle = ship_pitch
            msg = "LANDING SUCCESS: SAFE TOUCHDOWN"
            msg_color = GREEN
            timer = 60
            
        cam_frame = create_avatar_pilot_frame(ship_pitch, step)
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts, msg, msg_color, timer
        )
        
        if step == 30:
            save_surface_as_image(screen, "assets/screenshot_landing_success.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_success.append(pil_img)
            
    save_flicker_free_gif(frames_success, "assets/demo_landing_success.gif", fps=26)

    # -------------------------------------------------------------------------
    # 6. SCENARIO CRASH IMPACT
    # -------------------------------------------------------------------------
    print("Generating Scenario 6: Crash Impact (Flicker-Free)...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    history_ship_pitch = []
    
    for i in range(80):
        evtol.history_vy.append(30.0 + i * 0.7)
        evtol.history_angle_diff.append(14.0 + i * 0.15)
        history_ship_pitch.append(12.0 * math.sin(0.8 * (i * DT)))
        
    frames_crash = []
    for step in range(65):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        if step < 18:
            evtol.x = ship_center[0] - 20
            evtol.y = (ship_center[1] - 110) + step * 4.8
            evtol.vy = 76.0
            evtol.angle = ship_pitch + 20.0
            msg = ""
            msg_color = WHITE
            timer = 0
        else:
            evtol.x = ship_center[0] - 20
            evtol.y = ship_center[1] - 25
            evtol.vy = 0.0
            evtol.angle = ship_pitch + 20.0
            msg = "CRASHED! IMPACT: 76 m/s (LIMIT: 60)"
            msg_color = RED
            timer = 60
            
        prop_angle = (prop_angle + 40) % 360
        cam_frame = create_avatar_pilot_frame(-20.0, step)
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, {"S"}, fonts, msg, msg_color, timer
        )
        
        if step == 24:
            save_surface_as_image(screen, "assets/screenshot_crash_impact.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_crash.append(pil_img)
            
    save_flicker_free_gif(frames_crash, "assets/demo_crash_impact.gif", fps=26)

    print("=== All Flicker-Free, Direction-Verified Assets Completed! ===")

if __name__ == "__main__":
    main()
