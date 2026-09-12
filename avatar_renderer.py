import os
import cv2
import numpy as np
import math

AVATAR_BASE_PATH = os.path.join(os.path.dirname(__file__), "assets", "pilot_avatar_base.jpg")
_cached_base = None

def get_avatar_base(w=320, h=240):
    global _cached_base
    if _cached_base is not None:
        return _cached_base.copy()
    if os.path.exists(AVATAR_BASE_PATH):
        raw = cv2.imread(AVATAR_BASE_PATH)
        if raw is not None:
            bh, bw = raw.shape[:2]
            crop_w = int(bh * 4 / 3)
            if crop_w <= bw:
                start_x = (bw - crop_w) // 2
                cropped = raw[:, start_x:start_x + crop_w]
            else:
                cropped = raw
            _cached_base = cv2.resize(cropped, (w, h))
            return _cached_base.copy()
            
    fallback = np.zeros((h, w, 3), dtype=np.uint8)
    fallback[:, :] = (15, 22, 32)
    return fallback

def draw_realistic_hand(img, hand_angle_deg):
    """
    Renders realistic human hand positioned below face (chest level)
    with natural skin tone and MediaPipe tracking overlay.
    hand_angle_deg > 0: Tilts RIGHT (Clockwise)
    hand_angle_deg < 0: Tilts LEFT (Counter-Clockwise)
    """
    w, h = img.shape[1], img.shape[0]
    
    theta = math.radians(hand_angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    
    # Wrist at bottom center, leaving face/smile fully visible
    cx, cy = 160, 218
    lm0 = (cx, cy)
    
    def rot(dx, dy):
        return (int(cx + dx * cos_t - dy * sin_t), int(cy + dx * sin_t + dy * cos_t))
    
    # Anatomical finger joints pointing upwards towards chest
    lm_thumb = [rot(-18, -10), rot(-28, -22), rot(-34, -36), rot(-38, -48)]
    lm_index = [rot(-11, -22), rot(-15, -40), rot(-17, -58), rot(-18, -74)]
    lm_middle = [rot(0, -24), rot(0, -44), rot(0, -64), rot(0, -82)]
    lm_ring = [rot(11, -22), rot(14, -39), rot(16, -56), rot(17, -72)]
    lm_pinky = [rot(20, -16), rot(24, -30), rot(27, -44), rot(29, -58)]
    
    fingers = [lm_thumb, lm_index, lm_middle, lm_ring, lm_pinky]
    
    # 1. Realistic Flesh Hand Underlay
    skin_base = (175, 195, 235)    # BGR natural peach skin tone
    skin_shadow = (145, 165, 205)  # Edge shading
    
    # Forearm
    arm_pts = np.array([
        (cx - 30, h), (cx - 24, cy), (cx + 24, cy), (cx + 30, h)
    ], dtype=np.int32)
    cv2.fillPoly(img, [arm_pts], skin_base)
    cv2.polylines(img, [arm_pts], False, skin_shadow, 2)
    
    # Palm flesh polygon
    palm_pts = np.array([
        rot(-20, 8), lm_thumb[0], lm_index[0], lm_middle[0], lm_ring[0], lm_pinky[0], rot(20, 8), lm0
    ], dtype=np.int32)
    cv2.fillPoly(img, [palm_pts], skin_base)
    cv2.polylines(img, [palm_pts], True, skin_shadow, 2)
    
    # Finger flesh segments
    finger_radii = [10, 9, 9, 8, 7]
    for f, rad_base in zip(fingers, finger_radii):
        prev_pt = lm0 if f is lm_thumb or f is lm_pinky else f[0]
        for seg_idx, pt in enumerate(f):
            r = max(4, rad_base - seg_idx * 2)
            cv2.line(img, prev_pt, pt, skin_base, r * 2)
            cv2.circle(img, pt, r, skin_base, -1)
            if seg_idx < 3:
                cv2.circle(img, pt, r, skin_shadow, 1)
            prev_pt = pt
            
    # 2. MediaPipe Tracking Overlay (Real-time Vision Skeleton)
    green = (0, 255, 120)
    red = (30, 40, 255)
    yellow = (0, 235, 255)
    
    for f in fingers:
        prev = lm0 if (f is lm_thumb or f is lm_pinky) else f[0]
        cv2.line(img, lm0, f[0], green, 2)
        for pt in f:
            cv2.line(img, prev, pt, green, 2)
            cv2.circle(img, pt, 3, red, -1)
            prev = pt
    cv2.circle(img, lm0, 4, red, -1)
    
    # Control Vector Arrow (lm0 Wrist -> lm9 Middle MCP)
    lm9 = lm_middle[0]
    cv2.arrowedLine(img, lm0, lm9, yellow, 2, tipLength=0.22)

def create_avatar_pilot_frame(hand_angle_deg, frame_idx=0):
    w, h = 320, 240
    img = get_avatar_base(w, h)
    
    # Subtle dark gradient at bottom chest level
    for y in range(80):
        alpha = min(0.65, y / 80.0)
        img[h - 80 + y, :] = (img[h - 80 + y, :] * (1 - alpha) + np.array([12, 18, 26]) * alpha).astype(np.uint8)

    draw_realistic_hand(img, hand_angle_deg)
    
    # Top Left: Avatar Mask
    cv2.rectangle(img, (8, 6), (150, 22), (10, 15, 22), -1)
    cv2.putText(img, "AVATAR MASK: ACTIVE", (12, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 150), 1)
    
    # Top Right: Pitch value
    direction_txt = "RIGHT" if hand_angle_deg > 0.5 else ("LEFT" if hand_angle_deg < -0.5 else "LEVEL")
    pitch_str = f"PITCH: {hand_angle_deg:+.1f} deg [{direction_txt}]"
    cv2.rectangle(img, (w - 180, 6), (w - 8, 22), (10, 15, 22), -1)
    cv2.putText(img, pitch_str, (w - 176, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 240, 255), 1)
    
    # Bottom Center: Label
    cv2.putText(img, "3-DoF Body Pitch Coupled", (85, 232), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (200, 220, 240), 1)
    
    return img
