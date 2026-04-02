import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation

# --- Robot Parameters ---
LENGTHS = [100.0, 80.0, 125.0, 80.0, 100.0]
BASE_MASSES = [63.0, 260.0, 130.0, 280.0, 63.0]

plt.rcParams.update({
    'font.size': 24,
    'axes.titlesize': 28,
    'axes.labelsize': 24,
    'xtick.labelsize': 18,
    'ytick.labelsize': 18,
    'legend.fontsize': 18
})


def get_frozen_arched_geometry():
    """Generates a static, arched pose for the robot and drops it to the ground."""
    # Fixed parameters for a nice, visible arch
    phase_rad = np.radians(30)
    amp_rad = np.radians(60)
    lag = 1.0

    # 1. Kinematics
    joint_angles = np.zeros(4)
    for i in range(4):
        p_i = phase_rad + i * lag
        wave = np.sin(p_i) * amp_rad
        joint_angles[i] = max(0.0, wave) * -1.0

    angles = np.zeros(5)
    for i in range(4):
        angles[i + 1] = angles[i] + joint_angles[i]

    loc_x, loc_y = np.zeros(6), np.zeros(6)
    for i in range(5):
        loc_x[i + 1] = loc_x[i] + LENGTHS[i] * np.cos(angles[i])
        loc_y[i + 1] = loc_y[i] + LENGTHS[i] * np.sin(angles[i])

    # 2. Gravity Drop (Assuming balanced 150g/150g water for initial stable resting)
    masses = list(BASE_MASSES)
    masses[0] += 150.0
    masses[4] += 150.0
    total_mass = sum(masses)

    local_com_x = sum(masses[i] * (loc_x[i] + loc_x[i + 1]) / 2.0 for i in range(5)) / total_mass
    local_com_y = sum(masses[i] * (loc_y[i] + loc_y[i + 1]) / 2.0 for i in range(5)) / total_mass

    best_joints_x, best_joints_y = loc_x, loc_y
    min_energy = float('inf')

    for i in range(6):
        for j in range(i + 1, 6):
            dx = loc_x[j] - loc_x[i]
            dy = loc_y[j] - loc_y[i]
            if np.hypot(dx, dy) < 1e-5: continue

            angle = np.arctan2(dy, dx)
            cos_a, sin_a = np.cos(-angle), np.sin(-angle)

            rot_x = loc_x * cos_a - loc_y * sin_a
            rot_y = loc_x * sin_a + loc_y * cos_a
            shift_y = np.min(rot_y)
            rot_y -= shift_y

            if rot_y[i] < 1e-3 and rot_y[j] < 1e-3:
                com_x_rot = local_com_x * cos_a - local_com_y * sin_a
                com_y_rot = local_com_x * sin_a + local_com_y * cos_a - shift_y

                contact_xs = [rot_x[k] for k in range(6) if rot_y[k] < 1e-3]
                min_cx, max_cx = min(contact_xs), max(contact_xs)
                is_stable = (min_cx - 5.0) <= com_x_rot <= (max_cx + 5.0)

                score = com_y_rot + (0 if is_stable else 10000.0)
                if score < min_energy:
                    min_energy = score
                    best_joints_x, best_joints_y = rot_x, rot_y

    joints_x = best_joints_x - best_joints_x[0]
    joints_y = best_joints_y

    return joints_x, joints_y


def compute_dynamic_com(joints_x, joints_y, water_tail):
    """Calculates the CoM on the frozen geometry based ONLY on changing water mass."""
    water_head = 300.0 - water_tail

    masses = list(BASE_MASSES)
    masses[0] += water_tail
    masses[4] += water_head
    total_mass = sum(masses)

    com_x = sum(masses[i] * (joints_x[i] + joints_x[i + 1]) / 2.0 for i in range(5)) / total_mass
    com_y = sum(masses[i] * (joints_y[i] + joints_y[i + 1]) / 2.0 for i in range(5)) / total_mass

    # Calculate exact center points of the tail and head links for the water spheres
    tail_mid_x = (joints_x[0] + joints_x[1]) / 2.0
    tail_mid_y = (joints_y[0] + joints_y[1]) / 2.0
    head_mid_x = (joints_x[4] + joints_x[5]) / 2.0
    head_mid_y = (joints_y[4] + joints_y[5]) / 2.0

    return com_x, com_y, tail_mid_x, tail_mid_y, head_mid_x, head_mid_y, water_tail, water_head


def create_arched_water_shift_gif():
    print("Rendering Arched Water Shift Animation... Please wait.")

    fig, ax = plt.subplots(figsize=(16, 8), dpi=100)
    fig.subplots_adjust(left=0.05, right=0.75, top=0.85, bottom=0.15)

    # Pre-calculate the frozen pose once
    joints_x, joints_y = get_frozen_arched_geometry()

    frames = 60
    water_sweep = 150.0 + 150.0 * np.sin(np.linspace(0, 2 * np.pi, frames))

    def update(frame):
        ax.clear()

        current_water_tail = water_sweep[frame]
        com_x, com_y, tail_x, tail_y, head_x, head_y, w_tail, w_head = compute_dynamic_com(joints_x, joints_y,
                                                                                           current_water_tail)

        # 1. Draw Ground and Frozen Robot Body
        ax.axhline(0, color='brown', linewidth=6, linestyle='--')
        ax.plot(joints_x, joints_y, 'k-', linewidth=10, zorder=2, label='Robot Links')
        ax.scatter(joints_x, joints_y, color='black', s=150, zorder=3)

        # 2. Draw Dynamic Water Spheres at the Link Centers
        tail_size = 50 + (w_tail * 20)
        head_size = 50 + (w_head * 20)

        ax.scatter([tail_x], [tail_y], s=tail_size, color='cyan', alpha=0.7, zorder=4,
                   edgecolors='blue', linewidths=2, label='Tail Water Volume')
        ax.scatter([head_x], [head_y], s=head_size, color='blue', alpha=0.7, zorder=4,
                   edgecolors='darkblue', linewidths=2, label='Head Water Volume')

        # 3. Draw Center of Mass (CoM)
        ax.scatter([com_x], [com_y], color='magenta', marker='*', s=1200, zorder=5, label='Global CoM')
        ax.axvline(com_x, color='magenta', linestyle=':', linewidth=2, alpha=0.5)

        # 4. Readouts & HUD
        text_bg = dict(facecolor='white', alpha=0.9, edgecolor='black', boxstyle='round,pad=0.5')

        hud_text = (f"Tail Water: {w_tail:3.0f} g\n"
                    f"Head Water: {w_head:3.0f} g\n"
                    f"CoM X-Pos: {com_x:.1f} mm")
        ax.text(0.02, 0.95, hud_text, transform=ax.transAxes, fontsize=24, fontweight='bold',
                color='black', va='top', bbox=text_bg)

        # Labels directly next to the spheres (offset slightly depending on height)
        ax.text(tail_x, tail_y - 25, f"{w_tail:.0f}g", ha='center', va='top', fontsize=20, color='blue',
                fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))
        ax.text(head_x, head_y - 25, f"{w_head:.0f}g", ha='center', va='top', fontsize=20, color='darkblue',
                fontweight='bold', bbox=dict(facecolor='white', alpha=0.7, edgecolor='none', pad=1))

        # Formatting
        ax.set_aspect('equal')
        ax.set_xlim(-50, 550)
        ax.set_ylim(-100, 250)

        ax.set_title("Influence of Fluid Transfer on CoM (Arched Pose)", pad=20, fontweight='bold')
        ax.set_xlabel("Robot Length (mm)")

        ax.legend(loc='center left', bbox_to_anchor=(1.02, 0.5))
        ax.grid(True, alpha=0.3)

        return ax,

    anim = animation.FuncAnimation(fig, update, frames=frames, blit=False)

    filename = "arched_water_com_shift.gif"
    anim.save(filename, writer='pillow', fps=15)
    print(f"Success! Saved animation as {filename}")


if __name__ == '__main__':
    create_arched_water_shift_gif()