import matplotlib.pyplot as plt
import matplotlib.patches as patches

def create_architecture_diagram():
    fig, ax = plt.subplots(figsize=(14, 8), dpi=150)
    fig.patch.set_facecolor('#070c14')
    ax.set_facecolor('#070c14')
    
    # Title
    ax.text(7, 8.4, "MASS-eVTOL Autonomous Landing Simulator Architecture", 
            ha='center', va='center', fontsize=18, fontweight='bold', color='#00f0ff',
            family='sans-serif')
    ax.text(7, 8.0, "Hardware-in-the-Loop Vision HMI & Dynamic Wave Surface Feedback Flight Control System",
            ha='center', va='center', fontsize=11, color='#94a3b8', family='sans-serif')

    def draw_block(x, y, w, h, title, subtitle, border_col, bg_col, title_col='#ffffff'):
        box = patches.FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.08,rounding_size=0.15",
                                     edgecolor=border_col, facecolor=bg_col, linewidth=1.8)
        ax.add_patch(box)
        ax.text(x + w/2, y + h - 0.35, title, ha='center', va='center',
                fontsize=11, fontweight='bold', color=title_col)
        ax.text(x + w/2, y + h/2 - 0.2, subtitle, ha='center', va='center',
                fontsize=8.5, color='#cbd5e1', multialignment='center')

    def draw_arrow(x1, y1, x2, y2, label="", color='#00f0ff'):
        ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
                    arrowprops=dict(arrowstyle="->", color=color, lw=2.0, mutation_scale=16))
        if label:
            mid_x, mid_y = (x1 + x2)/2, (y1 + y2)/2 + 0.18
            ax.text(mid_x, mid_y, label, ha='center', va='center',
                    fontsize=8.5, color=color, fontweight='bold',
                    bbox=dict(boxstyle="round,pad=0.2", fc='#070c14', ec=color, lw=0.8))

    # Columns / Layers
    # Layer 1: Input & HMI
    draw_block(0.5, 5.0, 3.2, 2.2, "1. Vision HMI Sensing",
               "• WebCam DirectShow Feed\n• MediaPipe Hands 21-Landmarks\n• Wrist (lm0) - Middle (lm9) Vector\n• Pitch Angle Extraction: [-45°, +45°]",
               '#00f0ff', '#0d1d2e', '#00f0ff')
    
    draw_block(0.5, 1.8, 3.2, 2.2, "2. Pilot Manual Input",
               "• Pygame Keyboard Poller (WASD)\n• Dynamic Thrust Multiplier\n  (1.0x -> max 3.5x boost)\n• Mode Toggle Trigger [T Key]\n  (Manual <-> Autonomous FCS)",
               '#38bdf8', '#0d1d2e', '#38bdf8')

    # Layer 2: Core Flight Control System (FCS)
    draw_block(4.8, 4.4, 4.4, 2.8, "3. Autonomous FCS (PD Control Loop)",
               "• Dynamic Deck Pose Tracking\n  err_x = x_ship - x_drone\n  err_y = (y_deck - 25) - y_drone\n  err_θ = θ_ship - θ_drone\n• PID Feedback Acceleration Formulation:\n  ay = kp_y·err_y - kd_y·vy\n  ax = kp_x·err_x - kd_x·vx\n  α  = kp_a·err_θ",
               '#22c55e', '#0e261d', '#4ade80')

    draw_block(4.8, 1.2, 4.4, 2.4, "4. Ship Wave Dynamics Engine",
               "• Irregular Wave Heave Superposition:\n  heave = Σ A_i · sin(ω_i · t + φ_i)\n• Dynamic Deck Pitch Oscillation:\n  pitch = 14.0° · sin(0.8 · t + 0.4)\n• Real-time Helipad Tangent Slope: m(t)",
               '#a855f7', '#201335', '#c084fc')

    # Layer 3: Physical Simulator & Evaluator
    draw_block(10.2, 4.4, 3.3, 2.8, "5. Flight Physics & Touchdown",
               "• Gravity & Air Drag Damping\n  (vx, vy) · 0.95 dissipation\n• Deck Contact Boundary Detection\n• Safe Landing Verification:\n  Vy_impact < 60.0 m/s\n  |θ_drone - θ_ship| < 10.0°\n• Status: SUCCESS or CRASH",
               '#eab308', '#26200d', '#fde047')

    # Layer 4: Tactical HUD Dashboard
    draw_block(10.2, 1.2, 3.3, 2.4, "6. Tactical HUD Telemetry",
               "• Real-time Flight Dynamics HUD\n• 3-Channel Live Graphing:\n  - Pitch Deviation Error Curve\n  - Vertical Descent Rate (Vy)\n  - Ship Hull Wave Dynamics\n• Visual Vision HMI Subsurface",
               '#f43f5e', '#2c101a', '#fb7185')

    # Connections
    draw_arrow(3.7, 6.1, 4.8, 6.1, "Pitch Tilt Vector")
    draw_arrow(3.7, 2.9, 4.8, 4.7, "WASD / Mode T")
    draw_arrow(7.0, 3.6, 7.0, 4.4, "Ship Center & Slope (x, y, θ)")
    draw_arrow(9.2, 5.8, 10.2, 5.8, "Target Forces (ax, ay, α)")
    draw_arrow(9.2, 2.4, 10.2, 2.4, "Real-time Telemetry Data")
    draw_arrow(11.8, 4.4, 11.8, 3.6, "Touchdown Events")

    ax.set_xlim(0, 14)
    ax.set_ylim(0.5, 9.0)
    ax.axis('off')
    plt.tight_layout()
    plt.savefig("assets/system_architecture.png", facecolor=fig.get_facecolor(), edgecolor='none', bbox_inches='tight')
    print("Saved: assets/system_architecture.png")

if __name__ == "__main__":
    create_architecture_diagram()
