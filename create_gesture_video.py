"""
create_gesture_video.py
Generates a realistic MP4 video feed ('assets/pilot_gesture_feed.mp4')
showing a naval pilot wearing a flight helmet and aviator sunglasses
in a cockpit, reaching an outstretched arm and hand forward toward the camera
in foreshortened perspective, naturally tilting the hand left and right to control
eVTOL 3-DoF pitch.

This video is fed into cv2.VideoCapture in hand_tracker.py, where MediaPipe Hands
genuinely detects and tracks the wrist and finger skeleton in real time.
"""

import os
import cv2
import numpy as np
import math
import mediapipe as mp

def generate_pilot_gesture_video(output_path="assets/pilot_gesture_feed.mp4", total_frames=90, fps=30):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    bg_path = os.path.join(os.path.dirname(__file__), "assets", "pilot_avatar_base.jpg")
    if not os.path.exists(bg_path):
        # Fallback to brain artifact if not yet copied
        artifact_bg = r"C:\Users\Park\.gemini\antigravity-ide\brain\8971b28f-bce3-45a8-92e3-00f0e0754426\cool_pilot_sunglasses_1789207566612.jpg"
        if os.path.exists(artifact_bg):
            import shutil
            shutil.copyfile(artifact_bg, bg_path)
            
    bg_raw = cv2.imread(bg_path)
    if bg_raw is None:
        raise FileNotFoundError(f"Cannot load background avatar from {bg_path}")
        
    w, h = 640, 480
    bg_base = cv2.resize(bg_raw, (w, h))
    
    hand_path = os.path.join(os.path.dirname(__file__), "assets", "hand_navy_suit.png")
    if not os.path.exists(hand_path):
        hand_path = os.path.join(os.path.dirname(__file__), "hand_navy_suit.png")
    if not os.path.exists(hand_path):
        raise FileNotFoundError("assets/hand_navy_suit.png not found.")
        
    hand_bgra = cv2.imread(hand_path, cv2.IMREAD_UNCHANGED)
    
    target_h = 320
    target_w = int(hand_bgra.shape[1] * (target_h / hand_bgra.shape[0]))
    hand_scaled = cv2.resize(hand_bgra, (target_w, target_h), interpolation=cv2.INTER_LANCZOS4)
    
    # Palm rotation center in hand coordinates
    pc_x = int(target_w * 0.54)
    pc_y = int(target_h * 0.54)
    
    # Setup VideoWriter
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (w, h))
    
    hands_detector = mp.solutions.hands.Hands(
        static_image_mode=False,
        max_num_hands=1,
        min_detection_confidence=0.2,
        min_tracking_confidence=0.2
    )
    
    print(f"Generating {total_frames} frames of pilot gesture video at {w}x{h}...")
    
    detection_count = 0
    for i in range(total_frames):
        # Sinusoidal tilt cycle
        phase = 2.0 * math.pi * i / total_frames
        # delta_rot between -22 and +22 degrees
        delta_rot = 22.0 * math.sin(phase)
        
        # Subtle organic finger flexing and wrist lateral motion
        scale_factor = 1.0 + 0.015 * math.sin(phase * 2.0)
        sway_x = int(4.0 * math.cos(phase))
        sway_y = int(2.0 * math.sin(phase))
        
        # Cockpit micro-vibration
        bg_jitter_x = int(1.0 * math.sin(i * 0.8))
        bg_jitter_y = int(0.5 * math.cos(i * 0.9))
        
        # Jittered background
        M_bg = np.float32([[1, 0, bg_jitter_x], [0, 1, bg_jitter_y]])
        frame_bg = cv2.warpAffine(bg_base, M_bg, (w, h), borderMode=cv2.BORDER_REPLICATE)
        
        # Rotate and scale hand
        M_hand = cv2.getRotationMatrix2D((pc_x, pc_y), delta_rot, scale_factor)
        rot_hand = cv2.warpAffine(hand_scaled, M_hand, (target_w, target_h), flags=cv2.INTER_LANCZOS4)
        
        # Base placement: reaching from pilot shoulder toward camera
        ox = 160 + sway_x
        oy = 165 + sway_y
        
        composite = frame_bg.copy()
        h_clip = min(target_h, h - oy)
        w_clip = min(target_w, w - ox)
        
        if h_clip > 0 and w_clip > 0:
            alpha = (rot_hand[:h_clip, :w_clip, 3] / 255.0)[:, :, np.newaxis]
            hand_rgb = rot_hand[:h_clip, :w_clip, :3]
            bg_roi = composite[oy:oy+h_clip, ox:ox+w_clip]
            composite[oy:oy+h_clip, ox:ox+w_clip] = (bg_roi * (1.0 - alpha) + hand_rgb * alpha).astype(np.uint8)
            
        # Verify MediaPipe detection
        rgb_test = cv2.cvtColor(composite, cv2.COLOR_BGR2RGB)
        res = hands_detector.process(rgb_test)
        if res.multi_hand_landmarks:
            detection_count += 1
            
        writer.write(composite)
        
    writer.release()
    hands_detector.close()
    
    print(f"Video saved to {output_path}")
    print(f"MediaPipe detection success rate: {detection_count}/{total_frames} frames ({detection_count/total_frames*100:.1f}%)")

if __name__ == "__main__":
    generate_pilot_gesture_video()
