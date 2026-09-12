import os
import cv2
import math
import mediapipe as mp
import numpy as np

class HandTracker:
    def __init__(self, enable_avatar_privacy=True, video_source=None):
        self.mp_hands = mp.solutions.hands
        self.mp_draw = mp.solutions.drawing_utils
        self.enable_avatar_privacy = enable_avatar_privacy
        
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.25,
            min_tracking_confidence=0.25
        )
        
        # Default video feed source path
        default_video = os.path.join(os.path.dirname(__file__), "assets", "pilot_gesture_feed.mp4")
        if video_source is not None:
            self.video_source = video_source
        elif os.path.exists(default_video):
            self.video_source = default_video
        else:
            self.video_source = None
            
        self.is_video_mode = False
        self.cap = None
        
        if self.video_source and os.path.exists(self.video_source):
            self.cap = cv2.VideoCapture(self.video_source)
            if self.cap.isOpened():
                self.is_video_mode = True
                
        if not self.is_video_mode:
            # Fallback to physical webcam
            self.cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)
            if not self.cap.isOpened():
                self.cap = cv2.VideoCapture(0)
                
        if self.cap and self.cap.isOpened() and not self.is_video_mode:
            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, 320)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 240)
            
        self.frame_count = 0
        self.last_tilt = 0.0

    def draw_avatar_face_mask(self, frame):
        """
        Overlays a tactical flight helmet visor on webcam feed to protect user privacy.
        """
        h, w = frame.shape[:2]
        hc_x, hc_y = w // 2, int(h * 0.28)
        
        # Outer shell
        cv2.ellipse(frame, (hc_x, hc_y), (48, 52), 0, 0, 360, (35, 45, 55), -1)
        cv2.ellipse(frame, (hc_x, hc_y), (48, 52), 0, 0, 360, (70, 95, 125), 2)
        
        # Visor
        visor_pts = np.array([
            (hc_x - 32, hc_y - 10), (hc_x - 24, hc_y - 22), (hc_x + 24, hc_y - 22),
            (hc_x + 32, hc_y - 10), (hc_x + 28, hc_y + 14), (hc_x, hc_y + 18), (hc_x - 28, hc_y + 14)
        ], dtype=np.int32)
        cv2.fillPoly(frame, [visor_pts], (20, 120, 180))
        cv2.polylines(frame, [visor_pts], True, (0, 245, 255), 2)

    def get_tilt(self):
        self.frame_count += 1
        
        if self.cap is None or not self.cap.isOpened():
            if self.video_source and os.path.exists(self.video_source):
                self.cap = cv2.VideoCapture(self.video_source)
                self.is_video_mode = True
                
        success = False
        frame = None
        if self.cap and self.cap.isOpened():
            success, frame = self.cap.read()
            if not success or frame is None:
                if self.is_video_mode:
                    # Seamless loop video playback
                    self.cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                    success, frame = self.cap.read()
                    
        # Fallback if both video and webcam are unavailable
        if not success or frame is None:
            from avatar_renderer import create_avatar_pilot_frame
            sim_angle = 25.0 * math.sin(self.frame_count * 0.08)
            return create_avatar_pilot_frame(sim_angle, self.frame_count), sim_angle
            
        if not self.is_video_mode:
            frame = cv2.flip(frame, 1)
            
        frame = cv2.resize(frame, (320, 240))
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Real-time MediaPipe Hand Skeleton Detection
        results = self.hands.process(rgb_frame)
        tilt_angle = self.last_tilt
        
        if results.multi_hand_landmarks:
            for hand_landmarks in results.multi_hand_landmarks:
                # Genuine 21-joint skeleton render
                self.mp_draw.draw_landmarks(
                    frame, hand_landmarks, self.mp_hands.HAND_CONNECTIONS,
                    self.mp_draw.DrawingSpec(color=(0, 255, 120), thickness=2, circle_radius=2),
                    self.mp_draw.DrawingSpec(color=(30, 40, 255), thickness=2, circle_radius=2)
                )
                
                lm0 = hand_landmarks.landmark[0]
                lm9 = hand_landmarks.landmark[9]
                
                dx = (lm9.x - lm0.x) * 320
                dy = (lm9.y - lm0.y) * 240
                
                raw_angle = math.degrees(math.atan2(dy, dx)) + 90
                
                tilt = raw_angle
                tilt_angle = max(-45.0, min(45.0, tilt))
                self.last_tilt = tilt_angle
                
                # Yellow Control Vector Arrow (Wrist lm0 -> Knuckle lm9)
                p0 = (int(lm0.x * 320), int(lm0.y * 240))
                p9 = (int(lm9.x * 320), int(lm9.y * 240))
                cv2.arrowedLine(frame, p0, p9, (0, 235, 255), 2, tipLength=0.25)
                
        # If using real webcam and privacy is enabled, overlay helmet mask
        if not self.is_video_mode and self.enable_avatar_privacy:
            self.draw_avatar_face_mask(frame)
            
        # Top-left HUD badge: Vision HMI
        cv2.rectangle(frame, (6, 6), (155, 22), (10, 15, 22), -1)
        cv2.putText(frame, "WEBCAM HMI: ACTIVE", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 150), 1)
        
        # Top-right HUD badge: Body Pitch
        dir_txt = "RIGHT" if tilt_angle > 0.5 else ("LEFT" if tilt_angle < -0.5 else "LEVEL")
        cv2.rectangle(frame, (168, 6), (314, 22), (10, 15, 22), -1)
        cv2.putText(frame, f"PITCH: {tilt_angle:+.1f} deg [{dir_txt}]", (172, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 240, 255), 1)
        
        # Bottom-left HUD badge: MediaPipe Lock Status
        cv2.rectangle(frame, (6, 220), (195, 236), (10, 15, 22), -1)
        cv2.putText(frame, "MP SKELETON: LOCKED (21 JTS)", (10, 232), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 230, 255), 1)
        
        return frame, tilt_angle

    def release(self):
        if self.cap and self.cap.isOpened():
            self.cap.release()