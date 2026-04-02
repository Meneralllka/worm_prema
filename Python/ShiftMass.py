import sys
import numpy as np
from collections import deque
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout, QSlider, QLabel)
from PyQt5.QtCore import Qt, QTimer
import pyqtgraph as pg

# --- Robot Parameters ---
LENGTHS = [100.0, 80.0, 125.0, 80.0, 100.0]
BASE_MASSES = [63.0, 260.0, 130.0, 280.0, 63.0]


class WormRobotSim(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Planar Worm Robot Kinematics & Locomotion Simulation")
        self.resize(1300, 900)

        # State variables
        self.phase = 0.0
        self.phase_speed = 0.1
        self.frame_count = 0
        self.wave_type = 'Sine'
        self.dt = 0.030  # 30ms timer

        # Locomotion tracking
        self.global_offset_x = 0.0
        self.prev_grounded = []
        self.prev_global_x = np.zeros(6)
        self.prev_global_com_x = 0.0

        # Plot histories
        self.local_com_x_hist = deque(maxlen=40)
        self.local_com_y_hist = deque(maxlen=40)
        self.time_hist = deque(maxlen=300)
        self.disp_hist = deque(maxlen=300)
        self.vel_raw_hist = deque(maxlen=5)  # For smoothing
        self.vel_hist = deque(maxlen=300)

        # Toggle States
        self.tail_lifted = False
        self.neck_lifted = False
        self.head_lifted = False

        self.init_ui()

        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sim)
        self.timer.start(int(self.dt * 1000))

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        # --- Left Side: 2x2 Plot Grid ---
        plot_layout = QGridLayout()
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        # 1. Robot Motion (Top Left)
        self.plot_robot = pg.PlotWidget(title="1. Robot Motion (Keys 1-4: Wave | A,Y,X: Toggles)")
        self.plot_robot.setYRange(-20, 300)
        self.plot_robot.showGrid(x=True, y=True)
        self.robot_line = self.plot_robot.plot(pen=pg.mkPen('b', width=4), symbol='o', symbolBrush='b', symbolSize=8)
        self.com_point_robot = self.plot_robot.plot(pen=None, symbol='star', symbolSize=15, symbolBrush='r')
        plot_layout.addWidget(self.plot_robot, 0, 0)

        # 2. Local CoM Trajectory (Top Right)
        self.plot_com = pg.PlotWidget(title="2. Local CoM Trajectory (Gait Cycle)")
        self.plot_com.showGrid(x=True, y=True)
        self.com_path = self.plot_com.plot(pen=pg.mkPen('r', width=2), symbol='o', symbolSize=4, symbolBrush='r')
        plot_layout.addWidget(self.plot_com, 0, 1)

        # 3. Global Displacement (Bottom Left)
        self.plot_disp = pg.PlotWidget(title="3. Global X Displacement vs. Time")
        self.plot_disp.setLabel('left', 'Forward Distance (mm)')
        self.plot_disp.setLabel('bottom', 'Frames')
        self.plot_disp.showGrid(x=True, y=True)
        self.disp_line = self.plot_disp.plot(pen=pg.mkPen('g', width=3))
        plot_layout.addWidget(self.plot_disp, 1, 0)

        # 4. Linear Velocity (Bottom Right)
        self.plot_vel = pg.PlotWidget(title="4. Linear Velocity vs. Time")
        self.plot_vel.setLabel('left', 'Velocity (mm/s)')
        self.plot_vel.setLabel('bottom', 'Frames')
        self.plot_vel.showGrid(x=True, y=True)
        self.vel_line = self.plot_vel.plot(pen=pg.mkPen('m', width=3))  # Magenta
        plot_layout.addWidget(self.plot_vel, 1, 1)

        layout.addLayout(plot_layout, stretch=4)  # Give grid more width

        # --- Right Side: Controls & Status ---
        control_layout = QVBoxLayout()

        self.com_label = QLabel("Global CoM: (0.00, 0.00)")
        self.com_label.setStyleSheet("font-size: 16px; font-weight: bold; color: red; margin-bottom: 10px;")
        control_layout.addWidget(self.com_label)

        self.status_label = QLabel(self.get_status_text())
        self.status_label.setStyleSheet(
            "font-size: 14px; color: blue; margin-bottom: 20px; padding: 5px; border: 1px solid blue;")
        control_layout.addWidget(self.status_label)

        self.slider_water = self.create_slider("Water in Tail (L1) [g]", 0, 300, 150, control_layout)
        self.label_water_l5 = QLabel("Water in Head (L5): 150 g")
        self.label_water_l5.setStyleSheet("font-weight: bold; margin-bottom: 10px;")
        control_layout.addWidget(self.label_water_l5)

        self.slider_amp = self.create_slider("Wave Amplitude [deg]", 0, 90, 45, control_layout)
        self.slider_lag = self.create_slider("Lag Magnitude", 1, 30, 10, control_layout, scale=0.1)
        self.slider_power = self.create_slider("Sine Power (For Wave 4)", 10, 50, 20, control_layout, scale=0.1)

        control_layout.addStretch()
        layout.addLayout(control_layout, stretch=1)

    def create_slider(self, name, min_val, max_val, init_val, layout, scale=1.0):
        label = QLabel(f"{name}: {init_val * scale:.1f}")
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(init_val)

        if "Tail" in name:
            slider.valueChanged.connect(lambda val: label.setText(f"{name}: {val * scale:.1f}"))
            slider.valueChanged.connect(lambda val: self.label_water_l5.setText(f"Water in Head (L5): {300 - val} g"))
        else:
            slider.valueChanged.connect(lambda val: label.setText(f"{name}: {val * scale:.1f}"))

        layout.addWidget(label)
        layout.addWidget(slider)
        return slider

    def get_status_text(self):
        return (f"Active Wave: {self.wave_type}\n"
                f"Toggles Active:\n"
                f"Tail (A): {self.tail_lifted}\n"
                f"Neck (Y): {self.neck_lifted}\n"
                f"Head (X): {self.head_lifted}")

    def keyPressEvent(self, event):
        if event.key() == Qt.Key_1:
            self.wave_type = 'Sine'
        elif event.key() == Qt.Key_2:
            self.wave_type = 'Square'
        elif event.key() == Qt.Key_3:
            self.wave_type = 'Triangle'
        elif event.key() == Qt.Key_4:
            self.wave_type = 'Power Sine'
        elif event.key() == Qt.Key_A:
            self.tail_lifted = not self.tail_lifted
        elif event.key() == Qt.Key_Y:
            self.neck_lifted = not self.neck_lifted
        elif event.key() == Qt.Key_X:
            self.head_lifted = not self.head_lifted
        elif event.key() == Qt.Key_R:
            self.tail_lifted = False
            self.neck_lifted = False
            self.head_lifted = False

        self.status_label.setText(self.get_status_text())

    def update_sim(self):
        water_l1 = self.slider_water.value()
        water_l5 = 300.0 - water_l1
        amp_rad = np.radians(self.slider_amp.value())
        lag = self.slider_lag.value() * 0.1
        power = self.slider_power.value() * 0.1

        self.phase -= self.phase_speed
        self.frame_count += 1

        # 1. Forward Kinematics
        LIFT_SIDE = -1.0
        joint_angles = np.zeros(4)

        for i in range(4):
            if i == 0 and self.tail_lifted:
                joint_angles[i] = np.radians(-90)
            elif i == 2 and self.neck_lifted:
                joint_angles[i] = np.radians(90)
            elif i == 3 and self.head_lifted:
                joint_angles[i] = np.radians(90)
            else:
                p_i = self.phase + i * lag

                if self.wave_type == 'Sine':
                    wave = np.sin(p_i) * amp_rad
                elif self.wave_type == 'Square':
                    wave = np.sign(np.sin(p_i)) * amp_rad
                elif self.wave_type == 'Triangle':
                    wave = (2.0 / np.pi) * np.arcsin(np.sin(p_i)) * amp_rad
                elif self.wave_type == 'Power Sine':
                    wave = np.sign(np.sin(p_i)) * (np.abs(np.sin(p_i)) ** power) * amp_rad

                lift = max(0.0, wave)
                joint_angles[i] = lift * LIFT_SIDE

        angles = np.zeros(5)
        for i in range(4):
            angles[i + 1] = angles[i] + joint_angles[i]

        loc_x = np.zeros(6)
        loc_y = np.zeros(6)
        for i in range(5):
            loc_x[i + 1] = loc_x[i] + LENGTHS[i] * np.cos(angles[i])
            loc_y[i + 1] = loc_y[i] + LENGTHS[i] * np.sin(angles[i])

        # 2. Local CoM Base & Node Mass Mapping
        masses = list(BASE_MASSES)
        masses[0] += water_l1
        masses[4] += water_l5
        total_mass = sum(masses)

        local_com_x = sum(masses[i] * (loc_x[i] + loc_x[i + 1]) / 2.0 for i in range(5)) / total_mass
        local_com_y = sum(masses[i] * (loc_y[i] + loc_y[i + 1]) / 2.0 for i in range(5)) / total_mass

        # Calculate localized mass distribution per node (proxy for normal force)
        node_masses = np.zeros(6)
        for i in range(5):
            node_masses[i] += masses[i] / 2.0
            node_masses[i + 1] += masses[i] / 2.0

        # 3. Physics-Based Gravity Drop
        best_joints_x = loc_x
        best_joints_y = loc_y
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

        # 4. Anisotropic Friction (Weight-Dependent Ratchet Locomotion)
        grounded_nodes = [i for i, y in enumerate(joints_y) if y < 1.0]

        if self.frame_count == 1:
            self.prev_global_x = joints_x.copy()

        proposed_global_x = joints_x + self.global_offset_x
        correction = 0.0

        if grounded_nodes:
            # Gather the masses of only the nodes touching the ground
            grounded_masses = [node_masses[i] for i in grounded_nodes]
            total_grounded_mass = sum(grounded_masses)

            if total_grounded_mass > 0:
                for i, mass in zip(grounded_nodes, grounded_masses):
                    slip = proposed_global_x[i] - self.prev_global_x[i]
                    if slip < 0:  # Node is attempting to slide backwards
                        # Traction is proportional to the node's share of the grounded weight
                        traction_weight = mass / total_grounded_mass
                        correction += abs(slip) * traction_weight

        self.global_offset_x += correction
        global_joints_x = joints_x + self.global_offset_x
        self.prev_global_x = global_joints_x.copy()

        # 5. Global CoM recalculation
        global_com_x = sum(
            masses[i] * (global_joints_x[i] + global_joints_x[i + 1]) / 2.0 for i in range(5)) / total_mass
        global_com_y = sum(masses[i] * (joints_y[i] + joints_y[i + 1]) / 2.0 for i in range(5)) / total_mass

        # --- 6. Velocity Calculation ---
        if self.frame_count == 1:
            self.prev_global_com_x = global_com_x
            vel = 0.0
        else:
            # dx / dt (mm/s)
            vel = (global_com_x - self.prev_global_com_x) / self.dt

        self.prev_global_com_x = global_com_x

        # Add to raw history for smoothing
        self.vel_raw_hist.append(vel)
        smoothed_vel = sum(self.vel_raw_hist) / len(self.vel_raw_hist)
        # ------------------------------------

        # 7. Update Plots
        self.robot_line.setData(global_joints_x, joints_y)
        self.com_point_robot.setData([global_com_x], [global_com_y])
        self.plot_robot.setXRange(global_com_x - 150, global_com_x + 350)
        self.com_label.setText(f"Global CoM: ({global_com_x:.1f}, {global_com_y:.1f})")

        local_gait_x = global_com_x - global_joints_x[0]
        self.local_com_x_hist.append(local_gait_x)
        self.local_com_y_hist.append(global_com_y)
        self.com_path.setData(list(self.local_com_x_hist), list(self.local_com_y_hist))

        self.time_hist.append(self.frame_count)
        self.disp_hist.append(global_com_x)
        self.disp_line.setData(list(self.time_hist), list(self.disp_hist))

        self.vel_hist.append(smoothed_vel)
        self.vel_line.setData(list(self.time_hist), list(self.vel_hist))


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = WormRobotSim()
    window.setFocusPolicy(Qt.StrongFocus)
    window.show()
    sys.exit(app.exec_())