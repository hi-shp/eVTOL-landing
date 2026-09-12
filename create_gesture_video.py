"""
create_gesture_video.py
Generates a realistic 10-second MP4 video feed ('assets/pilot_gesture_feed.mp4', 300 frames at 30 fps)
showing a naval drone operator on a ship flight deck, reaching an outstretched arm and hand
forward toward the camera in dramatic foreshortened perspective, naturally tilting the hand
left and right to control eVTOL 3-DoF pitch.

This video is fed into cv2.VideoCapture in hand_tracker.py, where MediaPipe Hands
genuinely detects and tracks the wrist and finger skeleton in real time.
"""

import os
import cv2
import numpy as np
import math
import mediapipe as mp

def generate_pilot_gesture_video(output_path="assets/pilot_gesture_feed.mp4", total_frames=300, fps=30):
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    
    base_dir = os.path.dirname(__file__)
    orig_path = os.path.join(base_dir, "assets", "operator_candidate3_orig.jpg")
    bg_path = os.path.join(base_dir, "assets", "operator_candidate3_clean_bg.jpg")
    
    if not os.path.exists(orig_path):
        raise FileNotFoundError(f"Cannot load original operator image from {orig_path}")
    if not os.path.exists(bg_path):
        raise FileNotFoundError(f"Cannot load clean background from {bg_path}")
        
    img_orig = cv2.imread(orig_path)
    img_bg = cv2.imread(bg_path)
    h, w = img_orig.shape[:2]
    
    mp_hands = mp.solutions.hands.Hands(static_image_mode=True, max_num_hands=1)
    res = mp_hands.process(cv2.cvtColor(img_orig, cv2.COLOR_BGR2RGB))
    if not res.multi_hand_landmarks:
        raise RuntimeError("MediaPipe failed to detect hand in base image.")
        
    pts = np.array([(int(p.x * w), int(p.y * h)) for p in res.multi_hand_landmarks[0].landmark])
    wrist = pts[0]
    
    # Base with permanent sleeve connecting shoulder to wrist
    sleeve_mask = np.zeros((h, w), dtype=np.uint8)
    pts_sleeve = np.array([[460, 660], [530, 560], [620, 520], [670, 680], [580, 800], [480, 750]])
    cv2.fillPoly(sleeve_mask, [pts_sleeve], 255)
    sleeve_mask_f = cv2.GaussianBlur(sleeve_mask, (21, 21), 0).astype(np.float32) / 255.0
    
    base_with_sleeve = img_bg.astype(np.float32) * (1.0 - sleeve_mask_f[:, :, np.newaxis]) + img_orig.astype(np.float32) * sleeve_mask_f[:, :, np.newaxis]
    base_with_sleeve = np.clip(base_with_sleeve, 0, 255).astype(np.uint8)
    
    # Hand mask (only fingers and palm up to wrist cuff)
    hull = cv2.convexHull(pts)
    mask_hull = np.zeros((h, w), dtype=np.uint8)
    cv2.fillConvexPoly(mask_hull, hull, 255)
    mask_hull = cv2.dilate(mask_hull, cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (35, 35)))
    mask_hull[:, int(wrist[0]) + 25:] = 0
    hand_mask_f = cv2.GaussianBlur(mask_hull, (17, 17), 0).astype(np.float32) / 255.0
    hand_mask_3ch = hand_mask_f[:, :, np.newaxis]
    
    target_w, target_h = 640, 480
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    writer = cv2.VideoWriter(output_path, fourcc, fps, (target_w, target_h))
    
    mp_video_hands = mp.solutions.hands.Hands(min_detection_confidence=0.3, min_tracking_confidence=0.3)
    detected_count = 0
    
    print(f"Rendering {total_frames} frames ({total_frames/fps:.1f}s) to {output_path}...")
    
    for i in range(total_frames):
        t = i / float(fps)
        cycle_phase = 2.0 * math.pi * (t / 5.0)
        
        tilt_amp = 18.0 * math.sin(cycle_phase)
        rot_deg = -30.0 + tilt_amp
        
        micro_sway_y = 3.0 * math.sin(cycle_phase * 2.0)
        scale_flex = 1.0 + 0.012 * math.cos(cycle_phase * 2.0)
        
        px = float(wrist[0])
        py = float(wrist[1]) + micro_sway_y
        
        M = cv2.getRotationMatrix2D((px, py), rot_deg, scale_flex)
        rot_hand = cv2.warpAffine(img_orig, M, (w, h), flags=cv2.INTER_LANCZOS4)
        rot_mask = cv2.warpAffine(hand_mask_3ch, M, (w, h), flags=cv2.INTER_LANCZOS4)
        if len(rot_mask.shape) == 2:
            rot_mask = rot_mask[:, :, np.newaxis]
            
        comp = base_with_sleeve.astype(np.float32) * (1.0 - rot_mask) + rot_hand.astype(np.float32) * rot_mask
        comp = np.clip(comp, 0, 255).astype(np.uint8)
        
        frame_resized = cv2.resize(comp, (target_w, target_h), interpolation=cv2.INTER_AREA)
        
        r = mp_video_hands.process(cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB))
        if r.multi_hand_landmarks:
            detected_count += 1
            
        writer.write(frame_resized)
        
    writer.release()
    mp_video_hands.close()
    mp_hands.close()
    
    print(f"Done! MediaPipe detected in {detected_count}/{total_frames} frames ({detected_count/total_frames*100:.1f}%)")

if __name__ == "__main__":
    generate_pilot_gesture_video()
