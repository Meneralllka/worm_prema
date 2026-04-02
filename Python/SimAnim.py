import numpy as np
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation, PillowWriter

# --- Robot Parameters ---
LENGTHS = [100.0, 80.0, 125.0, 80.0, 100.0]
BASE_MASSES = [63.0, 260.0, 130.0, 280.0, 63.0]

# Add this near your imports to set a global baseline
plt.rcParams.update({'font.size': 32})


class WormRobotLoopingSim:
    def __init__(self, amplitude_deg, lag, filename):
        self.amp_rad = np.radians(amplitude_deg)
        self.lag = lag
        self.filename = filename

        self.total_frames = 60
        self.phase_speed = (2 * np.pi) / self.total_frames
        self.global_offset_x = 0.0
        self.prev_global_x = None

        # --- Updated Plot Styling ---
        self.fig, self.ax = plt.subplots(figsize=(12, 5))  # Slightly larger figure for larger text
        self.line, = self.ax.plot([], [], 'b-o', lw=4, markersize=8, zorder=3)
        self.com_point, = self.ax.plot([], [], 'r*', markersize=15, zorder=4)

        self.ax.axhline(0, color='black', lw=2, zorder=1)
        self.ax.set_aspect('equal')
        self.ax.grid(True, linestyle='--', alpha=0.3)

        # Increase Title size
        self.ax.set_title(f"Amplitude: {amplitude_deg}°, Lag: {lag}", fontsize=32, pad=15)

        # Increase Axis Label sizes
        self.ax.set_xlabel("X Position (mm)", fontsize=28)
        self.ax.set_ylabel("Y Position (mm)", fontsize=28)

        # Increase Tick Label sizes
        self.ax.tick_params(axis='both', which='major', labelsize=12)

    def get_robot_state(self, frame):
        phase = -frame * self.phase_speed
        joint_angles = np.zeros(4)

        # 1. Kinematics
        for i in range(4):
            p_i = phase + i * self.lag
            wave = np.sin(p_i) * self.amp_rad
            joint_angles[i] = max(0.0, wave) * -1.0

        angles = np.zeros(5)
        for i in range(4):
            angles[i + 1] = angles[i] + joint_angles[i]

        loc_x, loc_y = np.zeros(6), np.zeros(6)
        for i in range(5):
            loc_x[i + 1] = loc_x[i] + LENGTHS[i] * np.cos(angles[i])
            loc_y[i + 1] = loc_y[i] + LENGTHS[i] * np.sin(angles[i])

        # 2. Physics-Based Gravity Drop (Stability check)
        best_x, best_y = loc_x, loc_y
        min_energy = float('inf')
        for i in range(6):
            for j in range(i + 1, 6):
                dx, dy = loc_x[j] - loc_x[i], loc_y[j] - loc_y[i]
                if np.hypot(dx, dy) < 1e-5: continue
                angle = np.arctan2(dy, dx)
                cos_a, sin_a = np.cos(-angle), np.sin(-angle)
                rx = loc_x * cos_a - loc_y * sin_a
                ry = loc_x * sin_a + loc_y * cos_a
                ry -= np.min(ry)

                if ry[i] < 1e-3 and ry[j] < 1e-3:
                    score = np.mean(ry)
                    if score < min_energy:
                        min_energy = score
                        best_x, best_y = rx, ry

        # 3. Locomotion (Weight-Dependent Ratchet)
        best_x -= best_x[0]
        if self.prev_global_x is None:
            self.prev_global_x = best_x.copy()

        # Simplified anisotropic friction: if moving back, add to offset
        slip = np.min(best_x - self.prev_global_x)
        if slip < 0:
            self.global_offset_x += abs(slip)

        self.prev_global_x = best_x.copy()
        return best_x + self.global_offset_x, best_y

    def animate(self, i):
        x, y = self.get_robot_state(i)
        self.line.set_data(x, y)

        # CoM Tracking
        com_x = np.average(x, weights=np.append(BASE_MASSES, 0)[:6])
        com_y = np.mean(y)
        self.com_point.set_data([com_x], [com_y])

        # Camera follows the robot
        self.ax.set_xlim(com_x - 350, com_x + 350)
        self.ax.set_ylim(-20, 200)
        return self.line, self.com_point

    def run(self):
        ani = FuncAnimation(self.fig, self.animate, frames=self.total_frames, interval=30)
        ani.save(self.filename, writer=PillowWriter(fps=30))
        plt.close()


# --- Configuration Sets ---
sim_tasks = [
    (10, 1.0, "var_amp_10.gif"),
    (40, 1.0, "var_amp_40.gif"),
    (70, 1.0, "var_amp_70.gif"),
    (45, 0.2, "var_lag_02.gif"),
    (45, 1.2, "var_lag_12.gif"),
    (45, 2.2, "var_lag_22.gif"),
]

if __name__ == "__main__":
    for amp, lag, name in sim_tasks:
        print(f"Generating: {name} (Amp={amp}, Lag={lag})")
        WormRobotLoopingSim(amp, lag, name).run()
    print("All animations completed.")