import pygame
from config import DT

class eVTOLController:
    def __init__(self):
        self.x, self.y = 640, 100
        self.vx, self.vy = 0.0, 0.0
        self.angle = 0.0
        
        self.is_auto = False
        
        # 수동 조종 가속도를 위한 추력 배율 변수
        self.thrust_multiplier = 1.0
        
        # PID 게인
        self.kp_y, self.kd_y = 3.0, 1.5
        self.kp_x, self.kd_x = 2.0, 1.0
        self.kp_a, self.kd_a = 5.0, 0.5
        
        self.history_vy = []
        self.history_angle_diff = []

    def update(self, keys, cam_angle, ship_center, ship_pitch):
        ax, ay = 0.0, 0.0
        
        # 중력 적용
        ay += 40.0
        
        if not self.is_auto:
            # WASD 키 중 하나라도 누르고 있는지 확인
            is_pressing = keys[pygame.K_w] or keys[pygame.K_s] or keys[pygame.K_a] or keys[pygame.K_d]
            
            # 키를 꾹 누르고 있으면 추력 배율이 시간에 따라 점진적으로 증가 (최대 3.5배)
            if is_pressing:
                self.thrust_multiplier = min(self.thrust_multiplier + 2.0 * DT, 3.5)
            else:
                # 손을 떼면 즉시 기본 추력으로 초기화
                self.thrust_multiplier = 1.0
                
            # 기본 추력에 배율을 곱해서 최종 추력 계산
            base_thrust = 120.0
            current_thrust = base_thrust * self.thrust_multiplier
            
            if keys[pygame.K_w]: ay -= current_thrust
            if keys[pygame.K_s]: ay += current_thrust * 0.5
            if keys[pygame.K_a]: ax -= current_thrust * 0.6
            if keys[pygame.K_d]: ax += current_thrust * 0.6
            
            # 카메라 기울기에 따른 드론 기울기 동기화
            self.angle += (cam_angle - self.angle) * 0.1
            
        else:
            # [자동 착륙 모드] 선박 중앙과 기울기에 PID 수렴
            err_y = (ship_center[1] - 25) - self.y
            err_x = ship_center[0] - self.x
            err_a = ship_pitch - self.angle
            
            ay += self.kp_y * err_y - self.kd_y * self.vy
            ax += self.kp_x * err_x - self.kd_x * self.vx
            
            self.angle += (self.kp_a * err_a) * DT
            
        # 속도 및 위치 적분
        self.vx += ax * DT
        self.vy += ay * DT
        
        # 공기 저항 (감쇠)
        self.vx *= 0.95
        self.vy *= 0.95
        
        self.x += self.vx * DT
        self.y += self.vy * DT
        
        # 텔레메트리 데이터 기록
        self.history_vy.append(self.vy)
        self.history_angle_diff.append(abs(self.angle - ship_pitch))
        if len(self.history_vy) > 100: self.history_vy.pop(0)
        if len(self.history_angle_diff) > 100: self.history_angle_diff.pop(0)

    def reset_position(self):
        self.y = 100
        self.vy = 0
        self.vx = 0
        self.thrust_multiplier = 1.0