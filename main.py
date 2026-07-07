import pygame
import cv2
import sys
import math
from config import WIDTH, HEIGHT, FPS, WHITE, BLACK, GRAY, RED, GREEN, BLUE, YELLOW, CYAN, DARK_GRAY, MAX_LANDING_SPEED, MAX_ANGLE_DIFF
from hand_tracker import HandTracker
from ship_motion import ShipMotion
from controller import eVTOLController

def draw_text(surf, text, font, color, x, y):
    img = font.render(text, True, color)
    surf.blit(img, (x, y))

def draw_hud_box(screen, x, y, w, h, title, font_title):
    pygame.draw.rect(screen, (10, 15, 20, 200), (x, y, w, h))
    pygame.draw.rect(screen, (50, 100, 150), (x, y, w, h), 1)
    pygame.draw.rect(screen, (50, 100, 150), (x, y, w, 30))
    draw_text(screen, title, font_title, BLACK, x + 8, y + 5)

def draw_graph_axes(screen, x, y, w, h, max_val, min_val, y_unit, font_axis):
    # Y축 최대/최소값 및 단위
    draw_text(screen, f"{max_val} {y_unit}", font_axis, GRAY, x + 5, y + 35)
    draw_text(screen, f"{min_val} {y_unit}", font_axis, GRAY, x + 5, y + h - 20)
    # X축 단위
    draw_text(screen, "Time (s) ->", font_axis, GRAY, x + w - 70, y + h - 20)
    
    # 격자 가이드라인
    pygame.draw.line(screen, (40, 50, 60), (x, y + h/2 + 15), (x + w, y + h/2 + 15), 1)

def draw_wasd(screen, keys, font, x, y):
    size = 40
    pad_color = (60, 80, 100)
    active_color = CYAN
    
    positions = [
        (pygame.K_w, "W", x + size + 5, y),
        (pygame.K_a, "A", x, y + size + 5),
        (pygame.K_s, "S", x + size + 5, y + size + 5),
        (pygame.K_d, "D", x + (size + 5)*2, y + size + 5)
    ]
    
    for k_code, char, kx, ky in positions:
        color = active_color if keys[k_code] else pad_color
        pygame.draw.rect(screen, color, (kx, ky, size, size), border_radius=4)
        if not keys[k_code]:
            pygame.draw.rect(screen, (80, 100, 120), (kx, ky, size, size), 1, border_radius=4)
        draw_text(screen, char, font, BLACK if keys[k_code] else WHITE, kx + 12, ky + 10)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("MASS-eVTOL Landing Simulator")
    clock = pygame.time.Clock()
    
    font_xs = pygame.font.SysFont("consolas", 10)
    font_sm = pygame.font.SysFont("consolas", 14)
    font_md = pygame.font.SysFont("consolas", 20, bold=True)
    font_lg = pygame.font.SysFont("consolas", 40, bold=True)
    font_title_big = pygame.font.SysFont("consolas", 18, bold=True)

    tracker = HandTracker()
    ship = ShipMotion()
    evtol = eVTOLController()

    msg = ""
    msg_color = WHITE
    msg_timer = 0
    prop_angle = 0
    history_ship_pitch = []

    running = True
    while running:
        screen.fill((5, 10, 15))
        keys = pygame.key.get_pressed()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_t:
                    evtol.is_auto = not evtol.is_auto

        cam_frame, cam_angle = tracker.get_tilt()
        ship_center, p1, p2, ship_pitch = ship.update()
        evtol.update(keys, cam_angle, ship_center, ship_pitch)
        
        prop_angle = (prop_angle + 40) % 360
        
        # 선박 기울기 히스토리 저장 (3번째 그래프용)
        history_ship_pitch.append(ship_pitch)
        if len(history_ship_pitch) > 100:
            history_ship_pitch.pop(0)

        # 물리 충돌 판정
        if p2[0] != p1[0]:
            slope = (p2[1] - p1[1]) / (p2[0] - p1[0])
        else:
            slope = 0
            
        deck_y_at_drone_x = slope * (evtol.x - p1[0]) + p1[1]
        
        if min(p1[0], p2[0]) <= evtol.x <= max(p1[0], p2[0]):
            if evtol.y + 15 >= deck_y_at_drone_x:
                evtol.y = deck_y_at_drone_x - 15
                impact_v = abs(evtol.vy)
                angle_err = abs(evtol.angle - ship_pitch)
                evtol.vy = 0
                
                if impact_v > 1.0:
                    if impact_v < MAX_LANDING_SPEED and angle_err < MAX_ANGLE_DIFF:
                        msg = "LANDING SUCCESS"
                        msg_color = GREEN
                    else:
                        msg = f"CRASHED! IMPACT:{impact_v:.0f}"
                        msg_color = RED
                        
                    msg_timer = 120
                    evtol.reset_position()

        # 배경 선 그리기
        for i in range(0, WIDTH, 100):
            pygame.draw.line(screen, (20, 30, 40), (i, 0), (i, HEIGHT), 1)
        for i in range(0, HEIGHT, 100):
            pygame.draw.line(screen, (20, 30, 40), (0, i), (WIDTH, i), 1)

        # 디테일한 선체(Ship Hull) 렌더링
        rad = math.radians(ship_pitch)
        cos_r, sin_r = math.cos(rad), math.sin(rad)
        
        # 메인 선체 폴리곤
        ship_poly = [
            p1, p2, 
            (p2[0] - 50 * sin_r, p2[1] + 150 * cos_r), 
            (p1[0] + 50 * sin_r, p1[1] + 150 * cos_r)
        ]
        pygame.draw.polygon(screen, (40, 50, 60), ship_poly)
        
        # 함교(Bridge) 구조물 추가 (우측)
        bridge_poly = [
            (p2[0] - 80 * cos_r, p2[1] - 80 * sin_r),
            (p2[0] - 20 * cos_r, p2[1] - 20 * sin_r),
            (p2[0] - 20 * cos_r + 60 * sin_r, p2[1] - 20 * sin_r - 60 * cos_r),
            (p2[0] - 80 * cos_r + 60 * sin_r, p2[1] - 80 * sin_r - 60 * cos_r)
        ]
        pygame.draw.polygon(screen, (60, 70, 80), bridge_poly)
        
        # 함교 창문 디테일
        win_x = p2[0] - 70 * cos_r + 40 * sin_r
        win_y = p2[1] - 70 * sin_r - 40 * cos_r
        pygame.draw.circle(screen, CYAN, (int(win_x), int(win_y)), 4)
        win_x2 = p2[0] - 40 * cos_r + 40 * sin_r
        win_y2 = p2[1] - 40 * sin_r - 40 * cos_r
        pygame.draw.circle(screen, CYAN, (int(win_x2), int(win_y2)), 4)

        # 흘수선(Waterline) 디테일 (빨간선)
        wl_p1 = (p1[0] + 30 * sin_r, p1[1] + 90 * cos_r)
        wl_p2 = (p2[0] - 30 * sin_r, p2[1] + 90 * cos_r)
        pygame.draw.line(screen, (150, 40, 40), wl_p1, wl_p2, 4)

        # 메인 데크 및 타겟 마크
        pygame.draw.line(screen, (150, 160, 170), p1, p2, 6)
        pygame.draw.circle(screen, YELLOW, (int(ship_center[0]), int(ship_center[1])), 6)

        # 드론 렌더링
        drone_surf = pygame.Surface((80, 40), pygame.SRCALPHA)
        pygame.draw.rect(drone_surf, GRAY, (10, 15, 60, 6), border_radius=2)
        pygame.draw.rect(drone_surf, GREEN if evtol.is_auto else CYAN, (32, 5, 16, 10), border_radius=3)
        pygame.draw.line(drone_surf, WHITE, (20, 21), (20, 32), 2)
        pygame.draw.line(drone_surf, WHITE, (60, 21), (60, 32), 2)
        
        p_off = int(14 * math.cos(math.radians(prop_angle)))
        pygame.draw.line(drone_surf, RED, (10 - p_off, 10), (10 + p_off, 10), 2)
        pygame.draw.line(drone_surf, RED, (70 - p_off, 10), (70 + p_off, 10), 2)

        rotated_drone = pygame.transform.rotate(drone_surf, -evtol.angle)
        rect = rotated_drone.get_rect(center=(int(evtol.x), int(evtol.y)))
        screen.blit(rotated_drone, rect.topleft)

        # 텔레메트리 레이아웃: 데이터 텍스트 패널
        draw_hud_box(screen, 20, 20, 380, 120, "FLIGHT DYNAMICS", font_title_big)
        draw_text(screen, f"Vy (Speed) : {evtol.vy:5.1f} m/s", font_md, CYAN, 30, 55)
        draw_text(screen, f"DRONE PITCH: {evtol.angle:5.1f} deg", font_md, YELLOW, 30, 80)
        draw_text(screen, f"SHIP TARGET: {ship_pitch:5.1f} deg", font_md, GRAY, 30, 105)

        # 그래프 공통 설정
        gx, gw, gh = 20, 380, 170
        
        # 1. 피치 오차 그래프
        gy_pitch = 160
        draw_hud_box(screen, gx, gy_pitch, gw, gh, "PITCH DEVIATION ERROR", font_title_big)
        draw_graph_axes(screen, gx, gy_pitch, gw, gh, MAX_ANGLE_DIFF*3, 0, "deg", font_xs)
        pygame.draw.line(screen, RED, (gx, gy_pitch + gh - MAX_ANGLE_DIFF*3), (gx + gw, gy_pitch + gh - MAX_ANGLE_DIFF*3), 1)
        if len(evtol.history_angle_diff) > 1:
            pts_pitch = [(gx + 10 + i*(gw-20)/100, gy_pitch + gh - 10 - min(a*3, gh-40)) for i, a in enumerate(evtol.history_angle_diff)]
            pygame.draw.lines(screen, YELLOW, False, pts_pitch, 2)

        # 2. 수직 하강 속도 그래프
        gy_vert = 345
        draw_hud_box(screen, gx, gy_vert, gw, gh, "VERTICAL DESCENT RATE (Vy)", font_title_big)
        draw_graph_axes(screen, gx, gy_vert, gw, gh, MAX_LANDING_SPEED, 0, "m/s", font_xs)
        pygame.draw.line(screen, RED, (gx, gy_vert + gh - MAX_LANDING_SPEED), (gx + gw, gy_vert + gh - MAX_LANDING_SPEED), 1)
        if len(evtol.history_vy) > 1:
            pts_vert = [(gx + 10 + i*(gw-20)/100, gy_vert + gh - 10 - max(0, min(v, gh-40))) for i, v in enumerate(evtol.history_vy)]
            pygame.draw.lines(screen, CYAN, False, pts_vert, 2)

        # 3. 선박 파도 기울기(Wave Pitch) 그래프 추가
        gy_wave = 530
        draw_hud_box(screen, gx, gy_wave, gw, gh, "SHIP HULL WAVE PITCH", font_title_big)
        draw_graph_axes(screen, gx, gy_wave, gw, gh, "+20", "-20", "deg", font_xs)
        # 0도 기준선(가운데)
        pygame.draw.line(screen, (80, 100, 120), (gx, gy_wave + gh/2 + 10), (gx + gw, gy_wave + gh/2 + 10), 1)
        if len(history_ship_pitch) > 1:
            pts_wave = [(gx + 10 + i*(gw-20)/100, gy_wave + gh/2 + 10 - (p * 2.5)) for i, p in enumerate(history_ship_pitch)]
            pygame.draw.lines(screen, (150, 200, 255), False, pts_wave, 2)

        # 우측 웹캠 화면 렌더링
        if cam_frame is not None:
            rgb_cam_frame = cv2.cvtColor(cam_frame, cv2.COLOR_BGR2RGB)
            cam_w, cam_h = 400, 300
            rgb_cam_frame = cv2.resize(rgb_cam_frame, (cam_w, cam_h))
            cam_surface = pygame.surfarray.make_surface(rgb_cam_frame.swapaxes(0, 1))
            screen.blit(cam_surface, (WIDTH - cam_w - 20, 20))

        # WASD 조종 패널 및 모드 UI
        draw_wasd(screen, keys, font_md, WIDTH - 200, HEIGHT - 200)
        mode_txt = "MODE: AUTO" if evtol.is_auto else "MODE: MANUAL"
        draw_text(screen, mode_txt, font_md, GREEN if evtol.is_auto else CYAN, WIDTH - 220, HEIGHT - 90)
        draw_text(screen, "[T] Toggle Mode", font_sm, GRAY, WIDTH - 220, HEIGHT - 60)

        # 중앙 메시지 팝업
        if msg_timer > 0:
            pygame.draw.rect(screen, (0, 0, 0, 150), (WIDTH//2 - 250, HEIGHT//2 - 40, 500, 80))
            draw_text(screen, msg, font_lg, msg_color, WIDTH//2 - 230, HEIGHT//2 - 20)
            msg_timer -= 1

        pygame.display.flip()
        clock.tick(FPS)

    tracker.release()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()