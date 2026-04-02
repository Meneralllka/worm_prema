import sys
import numpy as np
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QSlider, QLabel, QMessageBox)
from PyQt5.QtCore import Qt

import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import matplotlib.animation as animation

# --- Robot Parameters ---
LENGTHS = [100.0, 80.0, 125.0, 80.0, 100.0]
BASE_MASSES = [63.0, 260.0, 130.0, 280.0, 63.0]
GRAVITY = 9.81  # m/s^2


class FBDWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Planar Worm Robot - FBD Generator (High Res & Stable)")
        self.resize(1800, 1000)  # Increased base window size for high-res viewing

        # Global Matplotlib Settings
        plt.rcParams.update({
            'font.size': 32,
            'axes.titlesize': 36,
            'axes.labelsize': 32,
            'xtick.labelsize': 24,
            'ytick.labelsize': 24,
            'legend.fontsize': 24
        })

        self.phase = 0.0
        self.global_offset_x = 0.0
        self.prev_global_x = None
        self.cycle_max_push = 0.0

        self.init_ui()
        self.update_cycle_max()
        self.update_fbd()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # Create a massive, high-DPI figure
        self.figure, self.ax = plt.subplots(figsize=(20, 12), dpi=100)

        # RIGID LAYOUT: This strictly locks the graph margins so it NEVER jumps.
        # It leaves 25% of the right side permanently empty for the legend.
        self.figure.subplots_adjust(left=0.05, right=0.75, top=0.88, bottom=0.12)

        self.canvas = FigureCanvas(self.figure)
        layout.addWidget(self.canvas, stretch=5)

        control_layout = QVBoxLayout()

        self.label_status = QLabel("Adjust parameters to view instantaneous FBD.")
        self.label_status.setStyleSheet("font-size: 16px; font-weight: bold; margin-bottom: 10px;")
        control_layout.addWidget(self.label_status)

        self.slider_phase = self.create_slider("Gait Phase [deg]", 0, 360, 0, control_layout)
        self.slider_water = self.create_slider("Water in Tail (L1) [g]", 0, 300, 150, control_layout)
        self.slider_amp = self.create_slider("Wave Amplitude [deg]", 0, 90, 45, control_layout)
        self.slider_lag = self.create_slider("Lag Magnitude", 1, 30, 10, control_layout, scale=0.1)

        control_layout.addSpacing(20)

        self.btn_reset_dist = QPushButton("Reset Distance Tracker")
        self.btn_reset_dist.clicked.connect(self.reset_distance)
        self.btn_reset_dist.setMinimumHeight(40)
        control_layout.addWidget(self.btn_reset_dist)

        control_layout.addSpacing(20)

        self.btn_save_png = QPushButton("Save Current FBD (PNG)")
        self.btn_save_png.clicked.connect(self.save_png)
        self.btn_save_png.setMinimumHeight(50)
        control_layout.addWidget(self.btn_save_png)

        self.btn_save_gif = QPushButton("Save Full Oscillation (GIF)")
        self.btn_save_gif.clicked.connect(self.save_gif)
        self.btn_save_gif.setMinimumHeight(50)
        self.btn_save_gif.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold; font-size: 16px;")
        control_layout.addWidget(self.btn_save_gif)

        control_layout.addStretch()
        layout.addLayout(control_layout, stretch=1)

    def create_slider(self, name, min_val, max_val, init_val, layout, scale=1.0):
        label = QLabel(f"{name}: {init_val * scale:.1f}")
        label.setStyleSheet("font-size: 14px;")
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(init_val)

        def on_change(val):
            label.setText(f"{name}: {val * scale:.1f}")
            if "Phase" not in name:
                self.update_cycle_max()
            self.update_fbd()

        slider.valueChanged.connect(on_change)
        layout.addWidget(label)
        layout.addWidget(slider)
        return slider

    def reset_distance(self):
        self.global_offset_x = 0.0
        self.prev_global_x = None
        self.update_fbd()

    def update_cycle_max(self):
        old_offset = self.global_offset_x
        old_prev = self.prev_global_x.copy() if self.prev_global_x is not None else None

        self.global_offset_x = 0.0
        self.prev_global_x = None

        max_p = 0.0
        for p in np.linspace(0, -2 * np.pi, 40):
            _, _, _, _, _, _, _, active_push = self.compute_kinematics(p)
            current_total_push = sum(active_push.values())
            if current_total_push > max_p:
                max_p = current_total_push

        self.cycle_max_push = max_p

        self.global_offset_x = old_offset
        self.prev_global_x = old_prev

    def compute_kinematics(self, phase_rad):
        water_l1 = self.slider_water.value()
        water_l5 = 300.0 - water_l1
        amp_rad = np.radians(self.slider_amp.value())
        lag = self.slider_lag.value() * 0.1

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

        masses = list(BASE_MASSES)
        masses[0] += water_l1
        masses[4] += water_l5

        node_masses = np.zeros(6)
        for i in range(5):
            node_masses[i] += masses[i] / 2.0
            node_masses[i + 1] += masses[i] / 2.0

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
        grounded_nodes = [i for i, y in enumerate(joints_y) if y < 1.0]

        if self.prev_global_x is None:
            self.prev_global_x = joints_x.copy()

        proposed_global_x = joints_x + self.global_offset_x
        correction = 0.0
        active_push = {i: 0.0 for i in range(6)}

        if grounded_nodes:
            grounded_masses = [node_masses[i] for i in grounded_nodes]
            total_grounded_mass = sum(grounded_masses)
            if total_grounded_mass > 0:
                for i, mass in zip(grounded_nodes, grounded_masses):
                    slip = proposed_global_x[i] - self.prev_global_x[i]
                    if slip < 0:
                        traction_weight = mass / total_grounded_mass
                        push_contribution = abs(slip) * traction_weight
                        correction += push_contribution
                        active_push[i] = push_contribution

        self.global_offset_x += correction
        global_joints_x = joints_x + self.global_offset_x
        self.prev_global_x = global_joints_x.copy()

        com_x = sum(masses[i] * (global_joints_x[i] + global_joints_x[i + 1]) / 2.0 for i in range(5)) / total_mass
        com_y = sum(masses[i] * (joints_y[i] + joints_y[i + 1]) / 2.0 for i in range(5)) / total_mass

        return global_joints_x, joints_y, masses, node_masses, grounded_nodes, com_x, com_y, active_push

    def draw_fbd_on_axes(self, ax, phase_rad):
        ax.clear()

        joints_x, joints_y, masses, node_masses, grounded_nodes, com_x, com_y, active_push = self.compute_kinematics(
            phase_rad)
        water_val = self.slider_water.value()
        amp_val = self.slider_amp.value()
        lag_val = self.slider_lag.value() * 0.1

        text_bg = dict(facecolor='white', alpha=0.9, edgecolor='none', pad=4)

        ax.axhline(0, color='brown', linewidth=6, linestyle='--', label='Ground')
        ax.plot(joints_x, joints_y, 'b-', linewidth=8, zorder=2)
        ax.scatter(joints_x, joints_y, color='black', s=250, zorder=3, label='Joints')
        ax.scatter([com_x], [com_y], color='magenta', marker='*', s=1000, zorder=4, label='CoM')

        # Increased arrow length and text spacing for a cleaner, wider look
        arrow_len = 100
        text_offset = 25

        # 1. Weights
        for i in range(5):
            mid_x = (joints_x[i] + joints_x[i + 1]) / 2.0
            mid_y = (joints_y[i] + joints_y[i + 1]) / 2.0
            weight_N = (masses[i] / 1000.0) * GRAVITY

            ax.arrow(mid_x, mid_y, 0, -arrow_len, width=3, head_width=15, head_length=20,
                     fc='red', ec='red', zorder=4, length_includes_head=True)
            ax.text(mid_x, mid_y - arrow_len - text_offset, f'{weight_N:.1f}N',
                    fontsize=32, color='red', ha='center', va='top', zorder=5, bbox=text_bg)

        # 2. Normal & Push
        for idx in grounded_nodes:
            norm_N = (node_masses[idx] / 1000.0) * GRAVITY
            ax.arrow(joints_x[idx], joints_y[idx], 0, arrow_len, width=3, head_width=15, head_length=20,
                     fc='green', ec='green', zorder=4, length_includes_head=True)
            ax.text(joints_x[idx], joints_y[idx] + arrow_len + text_offset, f'{norm_N:.1f}N',
                    fontsize=32, color='green', ha='center', va='bottom', zorder=5, bbox=text_bg)

            push_magnitude = active_push.get(idx, 0.0)
            if push_magnitude > 0.05:
                dynamic_dx = 50 + (push_magnitude * 20)
                ax.arrow(joints_x[idx], joints_y[idx], dynamic_dx, 0, width=3, head_width=15, head_length=20,
                         fc='orange', ec='orange', zorder=4, length_includes_head=True)
                ax.text(joints_x[idx] + dynamic_dx + text_offset, joints_y[idx], f'Push\n{push_magnitude:.1f}',
                        fontsize=24, color='orange', ha='left', va='center', zorder=5, bbox=text_bg)

        # HUD Top Left
        hud_text = (f"Distance Travelled: {self.global_offset_x:.1f} mm\n"
                    f"Peak Cycle Push: {self.cycle_max_push:.1f} Units")
        ax.text(0.02, 0.95, hud_text, transform=ax.transAxes, fontsize=32, fontweight='bold', color='black',
                va='top', bbox=dict(facecolor='white', alpha=0.9, edgecolor='black', boxstyle='round,pad=0.5'))

        # Legend strictly pinned to the right side
        ax.plot([], [], color='red', linewidth=5, label='Weight ($W$)')
        ax.plot([], [], color='green', linewidth=5, label='Normal Force ($N$)')
        ax.plot([], [], color='orange', linewidth=5, label='Active Push')
        ax.legend(loc='upper left', bbox_to_anchor=(1.02, 1.0))

        ax.set_aspect('equal')

        current_center_x = joints_x[0]
        # Pushed the limits slightly wider so axes bounds never collide with elements
        ax.set_xlim(current_center_x - 150, current_center_x + 550)
        ax.set_ylim(-250, 450)

        title_str = f"FBD Phase: {np.degrees(phase_rad):.0f}° | Water: {water_val}g | Amp: {amp_val}° | Lag: {lag_val:.1f}"
        ax.set_title(title_str, pad=30)
        ax.set_xlabel("X Position (mm)")
        ax.set_ylabel("Y Position (mm)")
        ax.grid(True, alpha=0.3)

    def update_fbd(self):
        phase_rad = np.radians(self.slider_phase.value())
        self.draw_fbd_on_axes(self.ax, phase_rad)

        # No more tight_layout() here! We rely on the rigid subplots_adjust set in init_ui.
        self.canvas.draw()

    def save_png(self):
        water = self.slider_water.value()
        amp = self.slider_amp.value()
        lag = self.slider_lag.value() * 0.1
        filename = f"fbd_water{water}_amp{amp}_lag{lag:.1f}.png"
        self.figure.savefig(filename, dpi=300, bbox_inches='tight')
        QMessageBox.information(self, "Success", f"Saved instantaneous FBD as {filename}")

    def save_gif(self):
        self.btn_save_gif.setText("Rendering... Please wait.")
        self.btn_save_gif.setEnabled(False)
        QApplication.processEvents()

        water = self.slider_water.value()
        amp = self.slider_amp.value()
        lag = self.slider_lag.value() * 0.1
        filename = f"robot_oscillation_W{water}_A{amp}_L{lag:.1f}.gif"

        self.reset_distance()
        self.update_cycle_max()

        fig_anim, ax_anim = plt.subplots(figsize=(20, 12), dpi=100)

        # Lock margins for the GIF exactly like the main window
        fig_anim.subplots_adjust(left=0.05, right=0.75, top=0.88, bottom=0.12)

        frames = 40
        phase_array = np.linspace(0, -2 * np.pi, frames)

        def update(frame):
            self.draw_fbd_on_axes(ax_anim, phase_array[frame])
            return ax_anim,

        anim = animation.FuncAnimation(fig_anim, update, frames=frames, blit=False)

        try:
            anim.save(filename, writer='pillow', fps=15)
            QMessageBox.information(self, "Success", f"Saved full oscillation animation as {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save GIF: {str(e)}")
        finally:
            plt.close(fig_anim)
            self.btn_save_gif.setText("Save Full Oscillation (GIF)")
            self.btn_save_gif.setEnabled(True)


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FBDWindow()
    window.show()
    sys.exit(app.exec_())