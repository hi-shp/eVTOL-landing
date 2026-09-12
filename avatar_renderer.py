import cv2
import numpy as np
import math

def create_avatar_pilot_frame(hand_angle_deg, frame_idx=0):
    """
    Renders a high-tech Cyber Pilot Avatar with helmet/visor masking the face
    for 100% privacy, along with natural hand tracking showing intuitive
    3-DoF pitch body-coupling.
    """
    w, h = 320, 240
    img = np.zeros((h, w, 3), dtype=np.uint8)
    
    # 1. Dark Tactical Cockpit Background
    for y in range(h):
        img[y, :] = (12 + int(8 * y / h), 16 + int(10 * y / h), 24 + int(14 * y / h))
    
    # Grid lines / Cockpit Canopy Frames
    cv2.line(img, (0, 70), (w, 70), (22, 32, 45), 1)
    cv2.line(img, (w//2, 0), (w//2, 110), (22, 32, 45), 1)
    cv2.line(img, (15, 15), (40, 15), (0, 200, 255), 1)
    cv2.line(img, (15, 15), (15, 40), (0, 200, 255), 1)
    cv2.line(img, (w - 15, 15), (w - 40, 15), (0, 200, 255), 1)
    cv2.line(img, (w - 15, 15), (w - 15, 40), (0, 200, 255), 1)

    # 2. Cyber Pilot Avatar (Helmet & Flight Suit)
    hc_x, hc_y = 160, 62
    
    # Flight Suit / Shoulders
    shoulder_pts = np.array([
        (50, 165), (90, 120), (125, 108), (195, 108), (230, 120), (270, 165),
        (270, 195), (50, 195)
    ], dtype=np.int32)
    cv2.fillPoly(img, [shoulder_pts], (26, 34, 44))
    cv2.polylines(img, [shoulder_pts], False, (45, 68, 92), 2)
    
    # Tactical Flight Vest & Patch
    cv2.rectangle(img, (132, 116), (188, 150), (36, 48, 62), -1)
    cv2.line(img, (160, 116), (160, 150), (0, 220, 255), 1)
    cv2.putText(img, "MASS-HMI", (136, 134), cv2.FONT_HERSHEY_SIMPLEX, 0.28, (0, 220, 255), 1)
    
    # Helmet Shell (Titanium & Kevlar Composite)
    cv2.ellipse(img, (hc_x, hc_y), (46, 50), 0, 0, 360, (32, 42, 54), -1)
    cv2.ellipse(img, (hc_x, hc_y), (46, 50), 0, 0, 360, (65, 88, 115), 2)
    
    # Helmet Top Crest / Sensor Ridge
    crest_pts = np.array([(148, 14), (172, 14), (168, 28), (152, 28)], dtype=np.int32)
    cv2.fillPoly(img, [crest_pts], (50, 65, 85))
    cv2.polylines(img, [crest_pts], True, (0, 220, 255), 1)
    
    # Cyber Visor (Neon Gold / Cyan Shield)
    visor_pts = np.array([
        (hc_x - 32, hc_y - 10),
        (hc_x - 24, hc_y - 22),
        (hc_x + 24, hc_y - 22),
        (hc_x + 32, hc_y - 10),
        (hc_x + 28, hc_y + 14),
        (hc_x, hc_y + 18),
        (hc_x - 28, hc_y + 14)
    ], dtype=np.int32)
    cv2.fillPoly(img, [visor_pts], (18, 110, 175))
    cv2.polylines(img, [visor_pts], True, (0, 245, 255), 2)
    
    # Visor Reflection Highlight
    cv2.line(img, (hc_x - 18, hc_y - 15), (hc_x + 12, hc_y - 15), (160, 240, 255), 2)
    cv2.line(img, (hc_x - 22, hc_y - 9), (hc_x - 4, hc_y - 9), (130, 215, 255), 1)
    
    # Tactical HUD Crosshair in Visor
    cv2.circle(img, (hc_x, hc_y - 2), 5, (0, 255, 180), 1)
    cv2.line(img, (hc_x - 8, hc_y - 2), (hc_x + 8, hc_y - 2), (0, 255, 180), 1)
    
    # Boom Microphone & Headset Units
    cv2.circle(img, (hc_x - 46, hc_y), 7, (50, 65, 85), -1)
    cv2.circle(img, (hc_x + 46, hc_y), 7, (50, 65, 85), -1)
    cv2.line(img, (hc_x - 44, hc_y + 5), (hc_x - 16, hc_y + 25), (75, 90, 110), 3)
    cv2.circle(img, (hc_x - 14, hc_y + 27), 4, (15, 15, 20), -1)
    cv2.circle(img, (hc_x - 14, hc_y + 27), 2, (0, 255, 100), -1) # Green mic LED
    
    # 3. Pilot's Hand & MediaPipe Skeleton Overlay
    rad = math.radians(hand_angle_deg - 90)
    cx, cy = 160, 178 # positioned comfortably in chest area
    cos_a, sin_a = math.cos(rad), math.sin(rad)
    
    lm0 = (cx, cy + 34) # Wrist
    def rot(dx, dy):
        return (int(cx + dx * cos_a - dy * sin_a), int(cy + dx * sin_a + dy * cos_a))
    
    lm_thumb = [rot(-24, 10), rot(-34, -4), rot(-40, -18), rot(-44, -32)]
    lm_index = [rot(-12, -8), rot(-16, -26), rot(-18, -42), rot(-20, -56)]
    lm_middle = [rot(0, -10), rot(0, -30), rot(0, -50), rot(0, -68)]
    lm_ring = [rot(12, -8), rot(15, -26), rot(16, -42), rot(18, -54)]
    lm_pinky = [rot(24, -4), rot(28, -18), rot(30, -32), rot(32, -44)]
    
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
    
    # 4. HUD Telemetry Overlay
    # Top Left: Privacy Avatar Badge
    cv2.rectangle(img, (8, 6), (160, 22), (10, 15, 22), -1)
    cv2.putText(img, "AVATAR MASK: PROTECTED", (10, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (0, 255, 150), 1)
    
    # Top Left: 3-DoF Body Pitch readout
    cv2.rectangle(img, (8, 26), (175, 42), (10, 15, 22), -1)
    cv2.putText(img, f"3-DoF Body Pitch: {hand_angle_deg:+.1f} deg", (10, 38), cv2.FONT_HERSHEY_SIMPLEX, 0.38, (0, 240, 255), 1)
    
    # Bottom Center: Intuitive 3-DoF Landing System label
    cv2.putText(img, "Natural Body-Coupled Landing FCS", (10, 230), cv2.FONT_HERSHEY_SIMPLEX, 0.36, (170, 185, 200), 1)
    
    return img
