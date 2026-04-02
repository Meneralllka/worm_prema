import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation

# --- Physical Dimensions (mm) ---
L1 = 185.0
L2 = 175.0

# --- CPG Parameters ---
ALPHA = 15.0
MU = 1.0
OMEGA = -3.0  # Speed of the gait
STEP_X_SIZE = 80  # Half-width of the step in mm
STEP_Y_SIZE = 40  # Step height in mm
GROUND_Y = -280  # How far down the floor is from the ceiling
FLATNESS = 0.8  # 1.0 is a perfectly flat line on the floor

# --- Initial State ---
x_cpg, y_cpg = 0.1, 0.0
dt = 0.03


def calculate_ik(x, y):
    dist_sq = x ** 2 + y ** 2
    dist = np.sqrt(dist_sq)

    # Reachability Check
    if dist > (L1 + L2) or dist < abs(L1 - L2):
        return None, None

    # Knee Angle (Theta 2)
    cos_t2 = (dist_sq - L1 ** 2 - L2 ** 2) / (2 * L1 * L2)
    # We choose the 'elbow back' configuration (typical for legs)
    sin_t2 = np.sqrt(max(0, 1 - cos_t2 ** 2))
    th2_rad = np.arctan2(sin_t2, cos_t2)

    # Hip Angle (Theta 1)
    th1_rad = np.arctan2(y, x) - np.arctan2(L2 * sin_t2, L1 + L2 * cos_t2)

    return th1_rad, th2_rad


# --- Visualization Setup ---
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Plot 1: The Visual Robot
ax1.set_xlim(-250, 250);
ax1.set_ylim(-400, 50)
ax1.axhline(0, color='black', lw=3)  # Ceiling
ax1.axhline(GROUND_Y, color='brown', lw=2, ls='--')  # Floor
leg_line, = ax1.plot([], [], 'ro-', lw=5, ms=10)
path_line, = ax1.plot([], [], 'cyan', alpha=0.3)

# Plot 2: Servo Angles (0-180)
ax2.set_ylim(-10, 190);
ax2.set_xlim(0, 100)
ax2.set_ylabel("Degrees")
ax2.set_title("Real-time Servo Positions")
hip_val, = ax2.plot([], [], label="Hip (Servo 1)")
knee_val, = ax2.plot([], [], label="Knee (Servo 2)")
ax2.legend()

hist_x, hist_y = [], []
hist_hip, hist_knee = [], []


def update(frame):
    global x_cpg, y_cpg

    # 1. CPG Step
    r2 = x_cpg ** 2 + y_cpg ** 2
    x_cpg += (ALPHA * (MU - r2) * x_cpg - OMEGA * y_cpg) * dt
    y_cpg += (ALPHA * (MU - r2) * y_cpg + OMEGA * x_cpg) * dt

    # 2. Map CPG to Cartesian Trajectory
    target_x = x_cpg * STEP_X_SIZE
    # Create the flat bottom
    y_offset = y_cpg * STEP_Y_SIZE
    if y_cpg < 0: y_offset *= (1 - FLATNESS)
    target_y = GROUND_Y + y_offset

    # 3. Solve IK
    th1_rad, th2_rad = calculate_ik(target_x, target_y)

    if th1_rad is not None:
        # 4. Map to Servo Degrees
        # In this coord system, -90 deg (straight down) = 90 deg servo
        s1 = np.degrees(th1_rad) + 180
        s2 = np.degrees(th2_rad)

        # Clip to physical servo limits
        s1 = np.clip(s1, 0, 180)
        s2 = np.clip(s2, 0, 180)

        # Forward Kinematics for drawing
        j2x = L1 * np.cos(th1_rad)
        j2y = L1 * np.sin(th1_rad)
        fx = j2x + L2 * np.cos(th1_rad + th2_rad)
        fy = j2y + L2 * np.sin(th1_rad + th2_rad)

        leg_line.set_data([0, j2x, fx], [0, j2y, fy])

        hist_x.append(fx);
        hist_y.append(fy)
        hist_hip.append(s1);
        hist_knee.append(s2)
        if len(hist_x) > 50:
            hist_x.pop(0);
            hist_y.pop(0)
            hist_hip.pop(0);
            hist_knee.pop(0)

        path_line.set_data(hist_x, hist_y)
        hip_val.set_data(range(len(hist_hip)), hist_hip)
        knee_val.set_data(range(len(hist_knee)), hist_knee)

    return leg_line, path_line, hip_val, knee_val


ani = FuncAnimation(fig, update, frames=200, interval=30, blit=True)
plt.tight_layout()
plt.show()