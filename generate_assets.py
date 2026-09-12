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

def create_synthetic_hand_frame(hand_angle_deg, frame_idx=0):
    w, h = 320, 240
    img = np.zeros((h, w, 3), dtype=np.uint8)
    # Background subtle room lighting gradient
    for y in range(h):
        img[y, :] = (18 + int(12 * y / h), 22 + int(14 * y / h), 30 + int(18 * y / h))
    
    # Tech camera crosshairs / guides
    cv2.line(img, (20, 20), (45, 20), (0, 180, 255), 1)
    cv2.line(img, (20, 20), (20, 45), (0, 180, 255), 1)
    cv2.line(img, (w - 20, 20), (w - 45, 20), (0, 180, 255), 1)
    cv2.line(img, (w - 20, 20), (w - 20, 45), (0, 180, 255), 1)
    cv2.line(img, (20, h - 20), (45, h - 20), (0, 180, 255), 1)
    cv2.line(img, (20, h - 20), (20, h - 45), (0, 180, 255), 1)
    cv2.line(img, (w - 20, h - 20), (w - 45, h - 20), (0, 180, 255), 1)
    cv2.line(img, (w - 20, h - 20), (w - 20, h - 45), (0, 180, 255), 1)
    
    # Hand center and rotation
    rad = math.radians(hand_angle_deg - 90)
    cx, cy = 160, 145
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    
    lm0 = (cx, cy + 45)
    def rot(dx, dy):
        return (int(cx + dx * cos_a - dy * sin_a), int(cy + dx * sin_a + dy * cos_a))
    
    lm_thumb = [rot(-35, 15), rot(-45, -5), rot(-52, -25), rot(-58, -45)]
    lm_index = [rot(-16, -10), rot(-22, -35), rot(-25, -55), rot(-28, -75)]
    lm_middle = [rot(0, -15), rot(0, -42), rot(0, -68), rot(0, -92)]
    lm_ring = [rot(16, -10), rot(20, -35), rot(22, -55), rot(24, -72)]
    lm_pinky = [rot(32, -5), rot(38, -25), rot(42, -42), rot(45, -58)]
    
    palm_pts = np.array([lm0, lm_thumb[0], lm_index[0], lm_middle[0], lm_ring[0], lm_pinky[0]], dtype=np.int32)
    cv2.fillPoly(img, [palm_pts], (42, 52, 62))
    
    fingers = [lm_thumb, lm_index, lm_middle, lm_ring, lm_pinky]
    green = (0, 255, 130)
    red = (30, 40, 255)
    yellow = (0, 220, 255)
    
    for f in fingers:
        prev = lm0 if f is lm_thumb or f is lm_pinky else f[0]
        cv2.line(img, lm0, f[0], green, 2)
        for pt in f:
            cv2.line(img, prev, pt, green, 2)
            cv2.circle(img, pt, 4, red, -1)
            prev = pt
    cv2.circle(img, lm0, 5, red, -1)
    
    lm9 = lm_middle[0]
    cv2.arrowedLine(img, lm0, lm9, yellow, 2, tipLength=0.25)
    
    cv2.putText(img, "MediaPipe Hands HMI [Tracking OK]", (12, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (0, 255, 180), 1)
    cv2.putText(img, f"Tilt Angle (lm0->lm9): {hand_angle_deg:+.1f} deg", (12, 42), cv2.FONT_HERSHEY_SIMPLEX, 0.42, (255, 255, 255), 1)
    cv2.putText(img, "Direct Drone Pitch Coupling", (12, 225), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (170, 180, 190), 1)
    
    return img

def render_simulator(screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
                     history_ship_pitch, cam_frame, active_keys, fonts, msg="", msg_color=WHITE, msg_timer=0):
    screen.fill((5, 10, 15))
    font_xs, font_sm, font_md, font_lg, font_title_big = fonts

    # 1. Background grid
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
    
    # Bridge Windows
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

    if evtol.is_auto:
        pygame.draw.line(screen, (80, 255, 130, 110), (int(evtol.x), int(evtol.y)), (int(deck_mid_x), int(deck_mid_y)), 1)
        draw_text(screen, "LOC: TRACKING DECK", font_xs, GREEN, int(evtol.x) + 48, int(evtol.y) - 10)

    # 4. Telemetry Panels & HUD
    draw_hud_box(screen, 20, 20, 380, 125, "FLIGHT DYNAMICS & TELEMETRY", font_title_big)
    draw_text(screen, f"Vy (Descent Rate) : {evtol.vy:5.1f} m/s", font_md, CYAN, 30, 52)
    draw_text(screen, f"Vx (Lateral Vel)  : {evtol.vx:5.1f} m/s", font_md, WHITE, 30, 74)
    draw_text(screen, f"DRONE PITCH       : {evtol.angle:5.1f} deg", font_md, YELLOW, 30, 96)
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

    # 5. Right Webcam & HMI Feed
    if cam_frame is not None:
        rgb_cam_frame = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
        cam_w, cam_h = 380, 240
        rgb_cam_frame = cv2.resize(rgb_cam_frame, (cam_w, cam_h))
        cam_surface = pygame.surfarray.make_surface(rgb_cam_frame.swapaxes(0, 1))
        cx, cy = WIDTH - cam_w - 20, 20
        pygame.draw.rect(screen, (35, 75, 115), (cx - 2, cy - 2, cam_w + 4, cam_h + 4), 2)
        screen.blit(cam_surface, (cx, cy))
        draw_text(screen, "HMI VISION TRACKER (MEDIAPIPE)", font_sm, CYAN, cx + 5, cy + cam_h + 8)

    # 6. WASD Controller Panel & Flight Mode Indicator
    draw_wasd(screen, active_keys, font_md, WIDTH - 220, HEIGHT - 220)
    mode_txt = "FCS MODE: [ AUTO LANDING ]" if evtol.is_auto else "FCS MODE: [ MANUAL FLIGHT ]"
    mode_color = GREEN if evtol.is_auto else CYAN
    draw_text(screen, mode_txt, font_md, mode_color, WIDTH - 260, HEIGHT - 85)
    draw_text(screen, "Press [T] to Toggle Autonomous FCS", font_sm, (160, 180, 200), WIDTH - 260, HEIGHT - 55)

    # 7. Impact / Touchdown Pop-up Notification
    if msg_timer > 0:
        box_w, box_h = 560, 80
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
    """
    Saves high frame count, smooth 1024x576 HD-optimized animated GIF.
    """
    if not frames:
        return
    duration_ms = int(1000.0 / fps)
    converted = []
    for f in frames:
        # High quality palette quantization with Floyd-Steinberg dithering
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
    font_lg = pygame.font.SysFont("consolas", 36, bold=True)
    font_title_big = pygame.font.SysFont("consolas", 16, bold=True)
    fonts = (font_xs, font_sm, font_md, font_lg, font_title_big)

    os.makedirs("assets", exist_ok=True)
    target_gif_size = (960, 540) # Sharp 16:9 HD resolution

    # -------------------------------------------------------------
    # 1. SCENARIO AUTO LANDING (High FPS Smooth Descent)
    # -------------------------------------------------------------
    print("Generating High-FPS Scenario 1: Auto Landing...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = True
    evtol.x = WIDTH // 2 - 90
    evtol.y = 110
    
    history_ship_pitch = []
    prop_angle = 0
    frames_auto = []
    
    for step in range(110): # 110 frames for super smooth motion
        ship_center, p1, p2, ship_pitch = ship.update()
        hand_tilt = ship_pitch * 0.85
        cam_frame = create_synthetic_hand_frame(hand_tilt, step)
        evtol.update({}, hand_tilt, ship_center, ship_pitch)
        
        prop_angle = (prop_angle + 40) % 360
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100:
            history_ship_pitch.pop(0)
            
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts, "", WHITE, 0
        )
        
        if step == 50:
            save_surface_as_image(screen, "assets/screenshot_main_hud.png")
            save_surface_as_image(screen, "assets/screenshot_auto_landing.png")
            save_surface_as_image(screen, "assets/screenshot_ship_wave_dynamics.png")
            # Save zoomed crops for detailed README showcases
            create_crop(screen, pygame.Rect(WIDTH - 400 - 20, 20, 400, 280), "assets/screenshot_mediapipe_hmi.png")
            create_crop(screen, pygame.Rect(20, 160, 380, 535), "assets/screenshot_telemetry_graphs.png")

        # Every frame for maximum smoothness!
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_auto.append(pil_img)
            
    save_high_fps_gif(frames_auto, "assets/demo_auto_landing.gif", fps=28)

    # -------------------------------------------------------------
    # 2. SCENARIO LANDING SUCCESS (Approach -> Touchdown -> Stable)
    # -------------------------------------------------------------
    print("Generating High-FPS Scenario 2: Landing Success Sequence...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = True
    evtol.x = WIDTH // 2
    
    for i in range(80):
        evtol.history_vy.append(45.0 - i * 0.25)
        evtol.history_angle_diff.append(max(0.8, 7.0 - i * 0.08))
        history_ship_pitch.append(8.0 * math.sin(0.8 * (i * DT)))
        
    frames_success = []
    for step in range(80):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        # Smooth approach to deck
        if step < 25:
            evtol.y = (ship_center[1] - 65) + step * 1.6
            evtol.vy = 28.0 - step * 0.4
            evtol.angle = ship_pitch - 1.2
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
            
        cam_frame = create_synthetic_hand_frame(ship_pitch, step)
        prop_angle = (prop_angle + 40) % 360
        
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, set(), fonts, msg, msg_color, timer
        )
        
        if step == 35:
            save_surface_as_image(screen, "assets/screenshot_landing_success.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_success.append(pil_img)
            
    save_high_fps_gif(frames_success, "assets/demo_landing_success.gif", fps=26)

    # -------------------------------------------------------------
    # 3. SCENARIO MANUAL FLIGHT (Hand Gesture Tilt & WASD Maneuvers)
    # -------------------------------------------------------------
    print("Generating High-FPS Scenario 3: Manual Flight & Hand Control...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    evtol.x = WIDTH // 2 - 140
    evtol.y = 220
    
    history_ship_pitch = []
    frames_manual = []
    
    for step in range(90):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        # Smooth hand tilt sine wave
        hand_tilt = 24.0 * math.sin(step * 0.08)
        cam_frame = create_synthetic_hand_frame(hand_tilt, step)
        
        active_keys = set()
        if (step // 15) % 2 == 0:
            active_keys.add("W")
        if step > 25 and step < 70:
            active_keys.add("D")
            
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

    # -------------------------------------------------------------
    # 4. SCENARIO CRASH IMPACT (Hard Descent Over Limit)
    # -------------------------------------------------------------
    print("Generating High-FPS Scenario 4: Crash Impact...")
    ship = ShipMotion()
    evtol = eVTOLController()
    evtol.is_auto = False
    
    for i in range(80):
        evtol.history_vy.append(30.0 + i * 0.7)
        evtol.history_angle_diff.append(14.0 + i * 0.15)
        history_ship_pitch.append(12.0 * math.sin(0.8 * (i * DT)))
        
    frames_crash = []
    for step in range(75):
        ship_center, p1, p2, ship_pitch = ship.update()
        
        if step < 20:
            evtol.x = ship_center[0] - 30
            evtol.y = (ship_center[1] - 120) + step * 4.8
            evtol.vy = 78.0
            evtol.angle = ship_pitch + 22.0
            msg = ""
            msg_color = WHITE
            timer = 0
        else:
            evtol.x = ship_center[0] - 30
            evtol.y = ship_center[1] - 25
            evtol.vy = 0.0
            evtol.angle = ship_pitch + 22.0
            msg = "CRASHED! IMPACT: 78 m/s (LIMIT: 60)"
            msg_color = RED
            timer = 60
            
        prop_angle = (prop_angle + 40) % 360
        cam_frame = create_synthetic_hand_frame(-22.0, step)
        
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100: history_ship_pitch.pop(0)
        
        render_simulator(
            screen, evtol, ship, ship_center, p1, p2, ship_pitch, prop_angle,
            history_ship_pitch, cam_frame, {"S"}, fonts, msg, msg_color, timer
        )
        
        if step == 26:
            save_surface_as_image(screen, "assets/screenshot_crash_impact.png")
            
        img_data = pygame.image.tostring(screen, "RGB")
        pil_img = Image.frombytes("RGB", (WIDTH, HEIGHT), img_data)
        pil_img = pil_img.resize(target_gif_size, Image.Resampling.LANCZOS)
        frames_crash.append(pil_img)
            
    save_high_fps_gif(frames_crash, "assets/demo_crash_impact.gif", fps=26)

    print("=== All High-FPS and High-Quality Visual Assets Completed! ===")

if __name__ == "__main__":
    main()
