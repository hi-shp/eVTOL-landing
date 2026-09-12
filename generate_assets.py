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

def draw_text(surf, text, font, color, x, y):
    img = font.render(text, True, color)
    surf.blit(img, (x, y))

def draw_hud_box(screen, x, y, w, h, title, font_title):
    pygame.draw.rect(screen, (8, 14, 22, 230), (x, y, w, h))
    pygame.draw.rect(screen, (40, 90, 140), (x, y, w, h), 1)
    pygame.draw.rect(screen, (25, 55, 85), (x, y, w, 28))
    draw_text(screen, title, font_title, CYAN, x + 8, y + 5)

def draw_graph_axes(screen, x, y, w, h, max_val, min_val, y_unit, font_axis):
    draw_text(screen, f"{max_val} {y_unit}", font_axis, (160, 170, 180), x + 5, y + 33)
    draw_text(screen, f"{min_val} {y_unit}", font_axis, (160, 170, 180), x + 5, y + h - 18)
    draw_text(screen, "Time (s) ->", font_axis, (140, 150, 160), x + w - 75, y + h - 18)
    pygame.draw.line(screen, (35, 48, 62), (x, y + h/2 + 14), (x + w, y + h/2 + 14), 1)

def draw_wasd(screen, active_keys, font, x, y):
    size = 40
    pad_color = (35, 50, 70)
    active_color = (0, 240, 255)
    
    positions = [
        ("W", "W", x + size + 5, y),
        ("A", "A", x, y + size + 5),
        ("S", "S", x + size + 5, y + size + 5),
        ("D", "D", x + (size + 5)*2, y + size + 5)
    ]
    
    for key_id, char, kx, ky in positions:
        is_active = key_id in active_keys
        color = active_color if is_active else pad_color
        pygame.draw.rect(screen, color, (kx, ky, size, size), border_radius=5)
        if not is_active:
            pygame.draw.rect(screen, (60, 85, 110), (kx, ky, size, size), 1, border_radius=5)
        draw_text(screen, char, font, BLACK if is_active else WHITE, kx + 13, ky + 10)

def render_simulator(screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
                     history_ship_pitch, cam_frame, active_keys, fonts, msg="", msg_color=WHITE, msg_timer=0,
                     extra_banner=""):
    screen.fill((5, 10, 15))
    font_xs, font_sm, font_md, font_lg, font_title_big = fonts

    # 1. Tactical grid
    for i in range(0, WIDTH, 80):
        pygame.draw.line(screen, (15, 25, 35), (i, 0), (i, HEIGHT), 1)
    for i in range(0, HEIGHT, 80):
        pygame.draw.line(screen, (15, 25, 35), (0, i), (WIDTH, i), 1)

    # Sea level
    sea_y = HEIGHT - 90
    pygame.draw.line(screen, (20, 50, 80), (0, sea_y), (WIDTH, sea_y), 2)
    sea_surf = pygame.Surface((WIDTH, 90), pygame.SRCALPHA)
    sea_surf.fill((10, 25, 45, 190))
    screen.blit(sea_surf, (0, sea_y))

    # 2. Ship Hull
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

    # 3. eVTOL Drone Rendering
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
        pygame.draw.line(drone_surf, (120, 210, 255, 140), (10, 20), (10, 36), 1)
        pygame.draw.line(drone_surf, (120, 210, 255, 140), (70, 20), (70, 36), 1)

    rotated_drone = pygame.transform.rotate(drone_surf, -evtol.angle)
    rect = rotated_drone.get_rect(center=(int(evtol.x), int(evtol.y)))
    screen.blit(rotated_drone, rect.topleft)

    # Attitude Reference Line from drone
    drone_rad = math.radians(-evtol.angle)
    ref_len = 55
    ref_x1 = evtol.x - ref_len * math.cos(drone_rad)
    ref_y1 = evtol.y - ref_len * math.sin(drone_rad)
    ref_x2 = evtol.x + ref_len * math.cos(drone_rad)
    ref_y2 = evtol.y + ref_len * math.sin(drone_rad)
    pygame.draw.line(screen, (0, 240, 255, 100), (int(ref_x1), int(ref_y1)), (int(ref_x2), int(ref_y2)), 1)

    if evtol.is_auto:
        pygame.draw.line(screen, (80, 255, 130, 110), (int(evtol.x), int(evtol.y)), (int(deck_mid_x), int(deck_mid_y)), 1)
        draw_text(screen, "LOC: TRACKING DECK", font_xs, GREEN, int(evtol.x) + 48, int(evtol.y) - 10)

    # 4. Telemetry Panels & HUD
    draw_hud_box(screen, 20, 20, 380, 125, "FLIGHT DYNAMICS & TELEMETRY", font_title_big)
    draw_text(screen, f"Vy (Descent Rate) : {evtol.vy:5.1f} m/s", font_md, CYAN, 30, 52)
    draw_text(screen, f"Vx (Lateral Vel)  : {evtol.vx:5.1f} m/s", font_md, WHITE, 30, 74)
    draw_text(screen, f"DRONE PITCH (θ_d) : {evtol.angle:5.1f} deg", font_md, YELLOW, 30, 96)
    draw_text(screen, f"SHIP DECK PITCH   : {ship_pitch:5.1f} deg", font_md, (150, 200, 255), 30, 118)

    gx, gw, gh = 20, 380, 165
    
    # 1. Pitch Deviation Error Graph
    gy_pitch = 160
    draw_hud_box(screen, gx, gy_pitch, gw, gh, "PITCH DEVIATION ERROR (|θ_drone - θ_ship|)", font_title_big)
    draw_graph_axes(screen, gx, gy_pitch, gw, gh, f"{MAX_ANGLE_DIFF:.0f}", "0", "deg", font_xs)
    threshold_y_pitch = gy_pitch + gh - 15 - int((MAX_ANGLE_DIFF / 30.0) * (gh - 45))
    pygame.draw.line(screen, (255, 80, 80, 180), (gx, threshold_y_pitch), (gx + gw, threshold_y_pitch), 1)
    draw_text(screen, "CRITICAL LIMIT (10°)", font_xs, RED, gx + gw - 130, threshold_y_pitch - 12)
    if len(evtol.history_angle_diff) > 1:
        pts_pitch = [(gx + 10 + i * (gw - 20) / 100, gy_pitch + gh - 15 - min(a * 2.8, gh - 45)) for i, a in enumerate(evtol.history_angle_diff)]
        pygame.draw.lines(screen, YELLOW, False, pts_pitch, 2)

    # 2. Vertical Velocity Graph
    gy_vert = 345
    draw_hud_box(screen, gx, gy_vert, gw, gh, "VERTICAL DESCENT RATE (Vy)", font_title_big)
    draw_graph_axes(screen, gx, gy_vert, gw, gh, f"{MAX_LANDING_SPEED:.0f}", "0", "m/s", font_xs)
    threshold_y_vert = gy_vert + gh - 15 - int((MAX_LANDING_SPEED / 80.0) * (gh - 45))
    pygame.draw.line(screen, (255, 80, 80, 180), (gx, threshold_y_vert), (gx + gw, threshold_y_vert), 1)
    draw_text(screen, "SAFE LIMIT (60 m/s)", font_xs, RED, gx + gw - 130, threshold_y_vert - 12)
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

    # 5. Right Webcam & Pilot Avatar HMI Feed
    if cam_frame is not None:
        rgb_cam_frame = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        cam_w, cam_h = 380, 240
        rgb_cam_frame = cv2.resize(rgb_cam_frame, (cam_w, cam_h))
        cam_surface = pygame.surfarray.make_surface(rgb_cam_frame.swapaxes(0, 1))
        cx, cy = WIDTH - cam_w - 20, 20
        pygame.draw.rect(screen, (35, 75, 115), (cx - 2, cy - 2, cam_w + 4, cam_h + 4), 2)
        screen.blit(cam_surface, (cx, cy))
        draw_text(screen, "VIRTUAL PILOT HMI (3-DoF BODY TRACKING)", font_sm, CYAN, cx + 5, cy + cam_h + 8)

    # 6. WASD Controller Panel & Flight Mode Indicator
    draw_wasd(screen, active_keys, font_md, WIDTH - 220, HEIGHT - 220)
    mode_txt = "FCS MODE: [ AUTO LANDING ]" if evtol.is_auto else "FCS MODE: [ 3-DoF MANUAL ]"
    mode_color = GREEN if evtol.is_auto else CYAN
    draw_text(screen, mode_txt, font_md, mode_color, WIDTH - 260, HEIGHT - 85)
    draw_text(screen, "Press [T] to Toggle Autonomous FCS", font_sm, (160, 180, 200), WIDTH - 260, HEIGHT - 55)

    # Top Center Banner (if any)
    if extra_banner:
        bw, bh = 600, 36
        bx = WIDTH // 2 - bw // 2
        pygame.draw.rect(screen, (10, 20, 35, 230), (bx, 15, bw, bh), border_radius=4)
        pygame.draw.rect(screen, (0, 220, 255), (bx, 15, bw, bh), 1, border_radius=4)
        b_img = font_md.render(extra_banner, True, (0, 240, 255))
        b_rect = b_img.get_rect(center=(WIDTH // 2, 15 + bh // 2))
        screen.blit(b_img, b_rect.topleft)

    # 7. Impact / Touchdown Pop-up Notification
    if msg_timer > 0:
        box_w, box_h = 620, 80
        popup_x = WIDTH // 2 - box_w // 2
        popup_y = HEIGHT // 2 - box_h // 2 - 40
        overlay = pygame.Surface((box_w, box_h), pygame.SRCALPHA)
        overlay.fill((8, 14, 22, 235))
        screen.blit(overlay, (popup_x, popup_y))
        pygame.draw.rect(screen, msg_color, (popup_x, popup_y, box_w, box_h), 2, border_radius=6)
        
        t_img = font_lg.render(msg, True, msg_color)
        t_rect = t_img.get_rect(center=(WIDTH // 2, popup_y + box_h // 2))
        screen.blit(t_img, t_rect.topleft)

def save_surface_as_image(surf, path):
    pygame.image.save(surf, path)
    print(f"Saved PNG: {path}")

def save_high_fps_gif(frames, path, fps=28):
    if not frames:
        return
    duration_ms = int(1000.0 / fps)
    converted = []
    for f in frames:
        p_img = f.convert("RGB").quantize(colors=256, method=Image.Resampling.LANCZOS, dither=Image.Dither.FLOYDSTEINBERG)
        converted.append(p_img)
        
    converted[0].save(
        path,
        save_all=True,
        append_images=converted[1:],
        duration=duration_ms,
        loop=0,
        optimize=True
    )
    size_mb = os.path.getsize(path) / (1024 * 1024)
    print(f"Saved High-Quality Smooth GIF: {path} ({len(frames)} frames @ {fps} FPS, {size_mb:.2f} MB)")

def create_crop(surf, rect, path):
    sub = surf.subsurface(rect)
    pygame.image.save(sub, path)
    print(f"Saved Cropped Detail PNG: {path}")

def main():
    os.environ["SDL_VIDEODRIVER"] = "dummy"
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    
    font_xs = pygame.font.SysFont("consolas", 11)
    font_sm = pygame.font.SysFont("consolas", 14)
    font_md = pygame.font.SysFont("consolas", 18, bold=True)
    font_lg = pygame.font.SysFont("consolas", 32, bold=True)
    font_title_big = pygame.font.SysFont("consolas", 16, bold=True)
    fonts = (font_xs, font_sm, font_md, font_lg, font_title_big)

    os.makedirs("assets", exist_ok=True)
    target_gif_size = (960, 540)

    # -------------------------------------------------------------------------
    # NEW SCENARIO A: 3-DoF NATURAL BODY-COUPLED TILT (Avatar Hand Sway <-> Drone Tilt)
    # -------------------------------------------------------------------------
    print("Generating NEW Scenario: 3-DoF Natural Body-Coupled Tilt...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = WIDTH // 2
    evtol.y = 220
    
    frames_tilt = []
    history_ship_pitch = []
    prop_angle = 0
    
    # 100 frames of rich smooth swaying from -32 deg to +32 deg
    for step in range(100):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        # Smooth wave for hand tilt: Left (-30 deg) to Right (+30 deg)
        hand_tilt = 30.0 * math.sin(step * 0.08)
        cam_frame = create_avatar_pilot_frame(hand_tilt, step)
        
        # Drone pitch dynamically couples to pilot's hand angle
        evtol.angle += (hand_tilt - evtol.angle) * 0.16
        evtol.vx = 18.0 * math.sin(step * 0.08)
        evtol.vy = -5.0 * math.cos(step * 0.08)
        evtol.x += evtol.vx * DT
        evtol.y += evtol.vy * DT
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        evtol.history_vy.append(evtol.vy)
        evtol.history_angle_diff.append(abs(evtol.angle - ship_pitch))
        if len(evtol.history_vy) > 100: evtol.history_vy.pop(0)
        if len(evtol.history_angle_diff) > 100: evtol.history_angle_diff.pop(0)
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts,
            "", WHITE, 0,
            extra_banner=f"3-DoF HMI COUPLING: Hand {hand_tilt:+.1f}° ➔ Drone Pitch {evtol.angle:+.1f}°"
        )
        
        if step == 20:
            save_surface_as_image(screen, "assets/screenshot_avatar_hmi_tilt.png")
            create_crop(screen, pygame.Rect(WIDTH - 400 - 20, 20, 400, 280), "assets/screenshot_mediapipe_hmi.png")
            create_crop(screen, pygame.Rect(WIDTH // 2 - 120, 160, 240, 140), "assets/screenshot_drone_tilt_zoom.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_tilt.append(pil_img)
        
    save_high_fps_gif(frames_tilt, "assets/demo_3dof_gesture_tilt.gif", fps=28)

    # -------------------------------------------------------------------------
    # NEW SCENARIO B: 2-DoF Landing (Crash) vs 3-DoF Landing (Safe Alignment)
    # -------------------------------------------------------------------------
    print("Generating NEW Scenario: 2-DoF vs 3-DoF Comparison...")
    frames_compare = []
    
    # --- PHASE 1: 2-DoF Approach (Level Attitude = 0 deg, Slope mismatch Crash) ---
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = WIDTH // 2
    evtol.angle = 0.0 # Fixed horizontal (2-DoF typical attitude)
    
    history_ship_pitch = []
    for step in range(50):
        ship_center, p1, p2, ship_pitch = ship.update()
        cam_frame = create_avatar_pilot_frame(0.0, step) # flat hand
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        if step < 28:
            evtol.y = (ship_center[1] - 110) + step * 3.2
            evtol.vy = 35.0
            evtol.angle = 0.0
            msg = ""
            msg_color = WHITE
            timer = 0
        else:
            evtol.y = ship_center[1] - 25
            evtol.vy = 0.0
            evtol.angle = 0.0
            msg = f"2-DoF FAILED: ANGLE MISMATCH ({abs(ship_pitch):.1f}° > 10°)"
            msg_color = RED
            timer = 60
            
        evtol.history_vy.append(evtol.vy)
        evtol.history_angle_diff.append(abs(evtol.angle - ship_pitch))
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts,
            msg, msg_color, timer,
            extra_banner="[COMPARISON] Conventional 2-DoF: Horizontal Attitude Only (Unstable On Wave)"
        )
        
        if step == 35:
            save_surface_as_image(screen, "assets/screenshot_2dof_crash_comparison.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_compare.append(pil_img)

    # --- PHASE 2: 3-DoF Approach (Hand aligns with Deck -> Perfect Touchdown) ---
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = WIDTH // 2
    
    for step in range(55):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        # Pilot naturally tilts hand to match the oscillating ship deck pitch
        hand_tilt = ship_pitch
        cam_frame = create_avatar_pilot_frame(hand_tilt, step)
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        if step < 26:
            evtol.y = (ship_center[1] - 100) + step * 2.9
            evtol.vy = 28.0
            evtol.angle = hand_tilt # synced with body
            msg = ""
            msg_color = WHITE
            timer = 0
        else:
            evtol.y = ship_center[1] - 25
            evtol.vy = 0.0
            evtol.angle = ship_pitch # 100% parallel to deck
            msg = "3-DoF SUCCESS: BODY-ALIGNED TOUCHDOWN"
            msg_color = GREEN
            timer = 60
            
        evtol.history_vy.append(evtol.vy)
        evtol.history_angle_diff.append(abs(evtol.angle - ship_pitch))
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts,
            msg, msg_color, timer,
            extra_banner="[COMPARISON] Proposed 3-DoF: Intuitive Body-Coupled Pitch Alignment (Stable)"
        )
        
        if step == 32:
            save_surface_as_image(screen, "assets/screenshot_3dof_attitude_alignment.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_compare.append(pil_img)
        
    save_high_fps_gif(frames_compare, "assets/demo_2dof_vs_3dof.gif", fps=26)

    # -------------------------------------------------------------------------
    # REFRESH SCENARIOS: Auto Landing, Manual Flight with Avatar Masking
    # -------------------------------------------------------------------------
    print("Refreshing Scenario 1: Auto Landing with Avatar HMI...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = True
    evtol.x = WIDTH // 2 - 90
    evtol.y = 110
    history_ship_pitch = []
    frames_auto = []
    
    for step in range(110):
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
        
        if step == 50:
            save_surface_as_image(screen, "assets/screenshot_main_hud.png")
            save_surface_as_image(screen, "assets/screenshot_auto_landing.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_auto.append(pil_img)
            
    save_high_fps_gif(frames_auto, "assets/demo_auto_landing.gif", fps=28)

    print("Refreshing Scenario 3: Manual Flight with Avatar HMI...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = WIDTH // 2 - 140
    evtol.y = 220
    history_ship_pitch = []
    frames_manual = []
    
    for step in range(90):
        ship_center, p1, p2, ship_pitch = ship.update()
        hand_tilt = 24.0 * math.sin(step * 0.08)
        cam_frame = create_avatar_pilot_frame(hand_tilt, step)
        
        active_keys = set()
        if (step // 15) % 2 == 0: active_keys.add("W")
        if step > 25 and step < 70: active_keys.add("D")
            
        evtol.angle += (hand_tilt - evtol.angle) * 0.14
        evtol.vx = 32.0 * math.sin(step * 0.08)
        evtol.vy = -18.0 if "W" in active_keys else 18.0
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
        
        if step == 40:
            save_surface_as_image(screen, "assets/screenshot_manual_flight.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_manual.append(pil_img)
            
    save_high_fps_gif(frames_manual, "assets/demo_manual_flight.gif", fps=26)

    print("=== All 3-DoF Body-Coupled & Avatar Visual Assets Generated! ===")

if __name__ == "__main__":
    main()
