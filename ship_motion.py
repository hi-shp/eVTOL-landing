# ship_motion.py
import math
from config import WIDTH, HEIGHT, DT, PREDICTION_STEPS

class ShipMotion:
    def __init__(self):
        self.time = 0.0
        self.base_y = HEIGHT - 150  # 선박 기본 흘수선 위치
        self.deck_width = 250       # 헬리패드 데크 길이
        
        # 파랑 주파수(Hz) 및 진폭(m) 중첩 데이터 (불규칙 파랑 모사)
        self.amplitudes = [35.0, 12.0]
        self.frequencies = [1.3, 2.7]
        self.phases = [0.0, 1.1]

    def _calculate_state(self, t):
        # 1. Heave (상하 거동) 수치 연산
        heave = 0.0
        for a, f, p in zip(self.amplitudes, self.frequencies, self.phases):
            heave += a * math.sin(f * t + p)
            
        # 2. Pitch (선체 회전/기울기) 수치 연산
        pitch = 14.0 * math.sin(0.8 * t + 0.4)
        
        y_center = self.base_y + heave
        angle_rad = math.radians(pitch)
        
        # 선체 패드의 양 끝점 좌표 계산 (기울기 반영)
        x1 = (WIDTH // 2) - (self.deck_width // 2) * math.cos(angle_rad)
        y1 = y_center - (self.deck_width // 2) * math.sin(angle_rad)
        x2 = (WIDTH // 2) + (self.deck_width // 2) * math.cos(angle_rad)
        y2 = y_center + (self.deck_width // 2) * math.sin(angle_rad)
        
        return (WIDTH // 2, y_center), (x1, y1), (x2, y2), pitch

    def update(self):
        self.time += DT
        return self._calculate_state(self.time)

    def get_future_prediction(self):
        # 모델 예측 제어(MPC) 시뮬레이션을 위한 미래 예측 타임라인 데이터
        prediction = []
        for step in range(PREDICTION_STEPS):
            future_t = self.time + (step * DT)
            center, _, _, _ = self._calculate_state(future_t)
            prediction.append(center[1])  # 미래 Y축 거동 저장
        return prediction