import os
import cv2
import numpy as np
import math
import mediapipe as mp

_shared_cap = None
_shared_hands = None
_shared_draw = None

def get_avatar_video_frame(frame_idx=0):
    global _shared_cap, _shared_hands, _shared_draw
    video_path = os.path.join(os.path.dirname(__file__), "assets", "pilot_gesture_feed.mp4")
    if not os.path.exists(video_path):
        return None, 0.0
        
    if _shared_cap is None or not _shared_cap.isOpened():
        _shared_cap = cv2.VideoCapture(video_path)
        
    total_frames = int(_shared_cap.get(cv2.CAP_PROP_FRAME_COUNT))
    if total_frames > 0:
        target_f = frame_idx % total_frames
        _shared_cap.set(cv2.CAP_PROP_POS_FRAMES, target_f)
        
    ret, frame = _shared_cap.read()
    if not ret or frame is None:
        return None, 0.0
        
    frame = cv2.resize(frame, (320, 240))
    
    if _shared_hands is None:
        _shared_hands = mp.solutions.hands.Hands(
            static_image_mode=False,
            max_num_hands=1,
            min_detection_confidence=0.25,
            min_tracking_confidence=0.25
        )
        _shared_draw = mp.solutions.drawing_utils
        
    rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
    res = _shared_hands.process(rgb)
    tilt_angle = 0.0
    if res.multi_hand_landmarks:
        for hand_landmarks in res.multi_hand_landmarks:
            _shared_draw.draw_landmarks(
                frame, hand_landmarks, mp.solutions.hands.HAND_CONNECTIONS,
                _shared_draw.DrawingSpec(color=(0, 255, 120), thickness=2, circle_radius=2),
                _shared_draw.DrawingSpec(color=(30, 40, 255), thickness=2, circle_radius=2)
            )
            lm0 = hand_landmarks.landmark[0]
            lm9 = hand_landmarks.landmark[9]
            dx = (lm9.x - lm0.x) * 320
            dy = (lm9.y - lm0.y) * 240
            raw_angle = math.degrees(math.atan2(dy, dx)) + 90
            tilt_angle = -(raw_angle - 27.0)
            tilt_angle = max(-45.0, min(45.0, tilt_angle))
            
            p0 = (int(lm0.x * 320), int(lm0.y * 240))
            p9 = (int(lm9.x * 320), int(lm9.y * 240))
            cv2.arrowedLine(frame, p0, p9, (0, 235, 255), 2, tipLength=0.25)
            
    cv2.rectangle(frame, (6, 6), (155, 22), (10, 15, 22), -1)
    cv2.putText(frame, "AVATAR MASK: ACTIVE", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 150), 1)
    
    dir_txt = "RIGHT" if tilt_angle > 0.5 else ("LEFT" if tilt_angle < -0.5 else "LEVEL")
    cv2.rectangle(frame, (168, 6), (314, 22), (10, 15, 22), -1)
    cv2.putText(frame, f"PITCH: {tilt_angle:+.1f} deg [{dir_txt}]", (172, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 240, 255), 1)
    
    cv2.rectangle(frame, (6, 220), (195, 236), (10, 15, 22), -1)
    cv2.putText(frame, "MP SKELETON: LOCKED (21 JTS)", (10, 232), cv2.FONT_HERSHEY_SIMPLEX, 0.32, (180, 230, 255), 1)
    
    return frame, tilt_angle

def create_avatar_pilot_frame(hand_angle_deg, frame_idx=0):
    frame, _ = get_avatar_video_frame(frame_idx)
    if frame is not None:
        return frame
        
    fallback = np.zeros((240, 320, 3), dtype=np.uint8)
    fallback[:, :] = (15, 22, 32)
    return fallback
