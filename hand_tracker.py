import cv2
import math
import mediapipe as mp
import numpy as np
from avatar_renderer import create_avatar_pilot_frame

class HandTracker:
    def __init__(self, enable_avatar_privacy=True):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.enable_avatar_privacy = enable_avatar_privacy
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        # Windows DirectShow backend for fast initialization
        self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
        if not self.cap.isOpened():
            self.cap = cv2.VideoCapture(0)
            
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
        
        self.frame_count = 0
        self.simulated_angle = 0.0

    def draw_avatar_face_mask(self, frame):
        """
        Overlays a high-tech pilot helmet on the upper face area to protect user privacy.
        """
        h, w = frame.shape[:2]
        hc_x, hc_y = w // 2, int(h * 0.28)
        
        # Helmet outer shell
        cv2.ellipse(frame, (hc_x, hc_y), (48, 52), 0, 0, 360, (35, 45, 55), -1)
        cv2.ellipse(frame, (hc_x, hc_y), (48, 52), 0, 0, 360, (70, 95, 125), 2)
        
        # Cyber Visor
        visor_pts = np.array([
            (hc_x - 32, hc_y - 10), (hc_x - 24, hc_y - 22), (hc_x + 24, hc_y - 22),
            (hc_x + 32, hc_y - 10), (hc_x + 28, hc_y + 14), (hc_x, hc_y + 18), (hc_x - 28, hc_y + 14)
        ], dtype=np.int32)
        cv2.fillPoly(frame, [visor_pts], (20, 120, 180))
        cv2.polylines(frame, [visor_pts], True, (0, 245, 255), 2)
        
        # Visor highlight & HUD
        cv2.line(frame, (hc_x - 18, hc_y - 15), (hc_x + 12, hc_y - 15), (160, 240, 255), 2)
        cv2.circle(frame, (hc_x, hc_y - 2), 5, (0, 255, 180), 1)
        
        # Privacy badge
        cv2.rectangle(frame, (8, 6), (155, 22), (10, 15, 22), -1)
        cv2.putText(frame, "AVATAR MASK: ACTIVE", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 150), 1)

    def get_tilt(self):
        self.frame_count += 1
        success, frame = False, None
        
        if self.cap.isOpened():
            success, frame = self.cap.read()
            
        # Fallback to simulated cyber pilot avatar if camera is unavailable or fails
        if not success or frame is None:
            self.simulated_angle = 25.0 * math.sin(self.frame_count * 0.05)
            synth_frame = create_avatar_pilot_frame(self.simulated_angle, self.frame_count)
            return synth_frame, self.simulated_angle
        
        frame = cv2.flip(frame, 1)
        frame = cv2.resize(frame, (320, 240))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        results = self.hands.process(rgb_frame)
        tilt_angle = 0.0
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 0), thickness=2, circle_radius=2),
                    self.mp_draw.DrawingSpec(color=(0, 0, 255), thickness=2, circle_radius=2)
                )
                
                lm0 = hand_landmarks.landmark[0]
                lm9 = hand_landmarks.landmark[9]
                
                dx = lm9.x - lm0.x
                dy = lm9.y - lm0.y
                
                angle = math.degrees(math.atan2(dy, dx))
                tilt_angle = angle + 90
                tilt_angle = max(-45.0, min(45.0, tilt_angle))
                
                # Draw yellow control vector arrow
                p0 = (int(lm0.x * 320), int(lm0.y * 240))
                p9 = (int(lm9.x * 320), int(lm9.y * 240))
                cv2.arrowedLine(frame, p0, p9, (0, 230, 255), 2, tipLength=0.25)
        
        # Protect user face with avatar helmet
        if self.enable_avatar_privacy:
            self.draw_avatar_face_mask(frame)
            
        cv2.putText(frame, f"Body Pitch: {tilt_angle:+.1f} deg", (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 240, 255), 1)
        return frame, tilt_angle

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()