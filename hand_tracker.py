import cv2
import math
import mediapipe as mp

class HandTracker:
    def __init__(self):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.7,
            min_tracking_confidence=0.7
        )
        
        self.cap = cv2.VideoCapture(0)
        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)

    def get_tilt(self):
        success, frame = self.cap.read()
        if not success:
            return None, 0.0
        
        frame = cv2.flip(frame, 1)
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
                
        return frame, tilt_angle

    def release(self):
        self.cap.release()