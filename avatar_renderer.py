import cv2
import numpy as np
import math

def create_avatar_pilot_frame(hand_angle_deg, frame_idx=0):
    """
    Renders Cyber Pilot Avatar.
    Positive hand_angle_deg (+deg) rotates CLOCKWISE (RIGHT on screen).
    Negative hand_angle_deg (-deg) rotates COUNTER-CLOCKWISE (LEFT on screen).
    """
    w, h = 320, 240
    img = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 1. Dark Cockpit Background (Uniform solid dark blue to prevent GIF palette flicker)
    img[:, :] = (14, 20, 30)
    
    # Canopy Frame lines
    cv2.line(img, (0, 65), (w, 65), (25, 38, 55), 1)
    cv2.line(img, (w//2, 0), (w//2, 100), (25, 38, 55), 1)
    cv2.line(img, (12, 12), (35, 12), (0, 180, 220), 1)
    cv2.line(img, (12, 12), (12, 35), (0, 180, 220), 1)
    cv2.line(img, (w - 12, 12), (w - 35, 12), (0, 180, 220), 1)
    cv2.line(img, (w - 12, 12), (w - 12, 35), (0, 180, 220), 1)

    # 2. Cyber Pilot Avatar (Helmet & Flight Suit)
    hc_x, hc_y = 160, 56
    
    # Flight Suit / Shoulders
    shoulder_pts = np.array([
        (55, 155), (95, 115), (125, 105), (195, 105), (225, 115), (265, 155),
        (265, 185), (55, 185)
    ], dtype=np.int32)
    cv2.fillPoly(img, [shoulder_pts], (26, 34, 46))
    cv2.polylines(img, [shoulder_pts], False, (45, 68, 92), 2)
    
    # Helmet Shell
    cv2.ellipse(img, (hc_x, hc_y), (44, 48), 0, 0, 360, (35, 45, 58), -1)
    cv2.ellipse(img, (hc_x, hc_y), (44, 48), 0, 0, 360, (70, 95, 125), 2)
    
    # Helmet Sensor Crest
    crest_pts = np.array([(148, 10), (172, 10), (168, 24), (152, 24)], dtype=np.int32)
    cv2.fillPoly(img, [crest_pts], (50, 65, 85))
    cv2.polylines(img, [crest_pts], True, (0, 220, 255), 1)
    
    # Cyber Visor (Neon Cyan Shield)
    visor_pts = np.array([
        (hc_x - 30, hc_y - 10),
        (hc_x - 22, hc_y - 20),
        (hc_x + 22, hc_y - 20),
        (hc_x + 30, hc_y - 10),
        (hc_x + 26, hc_y + 12),
        (hc_x, hc_y + 16),
        (hc_x - 26, hc_y + 12)
    ], dtype=np.int32)
    cv2.fillPoly(img, [visor_pts], (20, 110, 170))
    cv2.polylines(img, [visor_pts], True, (0, 245, 255), 2)
    
    # Visor Reflection Highlight
    cv2.line(img, (hc_x - 16, hc_y - 14), (hc_x + 10, hc_y - 14), (160, 240, 255), 2)
    cv2.circle(img, (hc_x, hc_y - 2), 4, (0, 255, 180), 1)
    
    # Boom Microphone & Headset
    cv2.circle(img, (hc_x - 44, hc_y), 6, (50, 65, 85), -1)
    cv2.circle(img, (hc_x + 44, hc_y), 6, (50, 65, 85), -1)
    cv2.line(img, (hc_x - 42, hc_y + 4), (hc_x - 15, hc_y + 23), (75, 90, 110), 2)
    cv2.circle(img, (hc_x - 14, hc_y + 24), 3, (0, 255, 100), -1)
    
    # 3. Pilot's Hand with Correct Clockwise Rotation
    # Angle in radians (standard math: positive angle is CCW, but screen y is inverted,
    # so standard rotation with x' = x cos θ - y sin θ rotates CLOCKWISE in screen coordinates!)
    # Let base vector be pointing upwards (dy < 0, dx = 0).
    # When hand_angle_deg > 0 (e.g. +30 deg), we want fingers to tilt RIGHT (dx > 0).
    # Rotation formula for screen coords where +y is down:
    # x' = cx + dx * cos(θ) - dy * sin(θ)
    # y' = cy + dx * sin(θ) + dy * cos(θ)
    # For dx = 0, dy = -r:
    # x' = cx - (-r) * sin(θ) = cx + r * sin(θ)
    # If θ > 0: sin(θ) > 0 ==> x' > cx (TILTS RIGHT!)
    # y' = cy + (-r) * cos(θ) = cy - r * cos(θ)
    theta = math.radians(hand_angle_deg)
    cos_t = math.cos(theta)
    sin_t = math.sin(theta)
    
    # Wrist position in lower center
    cx, cy = 160, 190
    lm0 = (cx, cy)
    
    def rot(dx, dy):
        return (int(cx + dx * cos_t - dy * sin_t), int(cy + dx * sin_t + dy * cos_t))
    
    # Hand finger joints relative to wrist (0, 0) pointing UP (dy negative)
    lm_thumb = [rot(-20, -10), rot(-28, -24), rot(-32, -36), rot(-35, -48)]
    lm_index = [rot(-10, -22), rot(-14, -38), rot(-16, -52), rot(-18, -66)]
    lm_middle = [rot(0, -24), rot(0, -42), rot(0, -58), rot(0, -74)]
    lm_ring = [rot(10, -22), rot(14, -38), rot(16, -52), rot(18, -64)]
    lm_pinky = [rot(20, -18), rot(24, -32), rot(26, -44), rot(28, -54)]
    
    # Glove Palm Fill
    palm_pts = np.array([lm0, lm_thumb[0], lm_index[0], lm_middle[0], lm_ring[0], lm_pinky[0]], dtype=np.int32)
    cv2.fillPoly(img, [palm_pts], (42, 54, 68))
    
    # Skeleton lines (MediaPipe green)
    fingers = [lm_thumb, lm_index, lm_middle, lm_ring, lm_pinky]
    green = (0, 255, 120)
    red = (30, 40, 255)
    yellow = (0, 230, 255)
    
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
    cv2.arrowedLine(img, lm0, lm9, yellow, 2, tipLength=0.25)
    
    # 4. HUD Labels (Carefully positioned to avoid overlap)
    # Top Left: Avatar Mask Protected
    cv2.rectangle(img, (8, 6), (150, 22), (10, 15, 22), -1)
    cv2.putText(img, "AVATAR MASK: ACTIVE", (12, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.35, (0, 255, 150), 1)
    
    # Top Right: Hand Pitch Value
    direction_txt = "RIGHT" if hand_angle_deg > 0.5 else ("LEFT" if hand_angle_deg < -0.5 else "CENTER")
    pitch_str = f"PITCH: {hand_angle_deg:+.1f} deg [{direction_txt}]"
    cv2.rectangle(img, (w - 180, 6), (w - 8, 22), (10, 15, 22), -1)
    cv2.putText(img, pitch_str, (w - 176, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.33, (0, 240, 255), 1)
    
    # Bottom Center: Label
    cv2.putText(img, "3-DoF Body Pitch Coupled", (85, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.34, (160, 175, 190), 1)
    
    return img

if __name__ == "__main__":
    # Test +30 deg (should tilt right on screen)
    img_right = create_avatar_pilot_frame(30.0)
    cv2.imwrite("assets/test_tilt_right.png", img_right)
    # Test -30 deg (should tilt left on screen)
    img_left = create_avatar_pilot_frame(-30.0)
    cv2.imwrite("assets/test_tilt_left.png", img_left)
    print("Test images saved: assets/test_tilt_right.png, assets/test_tilt_left.png")
