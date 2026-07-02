import sys
from collections import deque

import numpy as np
import pyqtgraph as pg
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (
    QApplication, QGridLayout, QHBoxLayout, QLabel,
    QMainWindow, QSlider, QVBoxLayout, QWidget, QFrame
)

# --- Physical Robot Parameters ---
LENGTHS = np.array([100.0, 80.0, 125.0, 80.0, 100.0], dtype=float)
BASE_MASSES = np.array([63.0, 260.0, 130.0, 280.0, 63.0], dtype=float)
PITCH_STIFFNESS = 0.15

# --- Hydrodynamic Parameters ---
RHO = 1000.0
C_N = 1.5  # Normal drag coefficient
C_T = 0.05  # Tangential (skin) drag coefficient
WIDTH = 120.0  # Link width (mm)


def solve_floating_kinematics_and_mass(phase, amplitude_rad, lag, water_l1):
    """
    Computes kinematics, calculates CoM, applies hydrostatic pitch,
    and returns the absolute geometry and final link angles.
    """
    joint_angles = np.zeros(4, dtype=float)
    for idx in range(4):
        phase_i = phase + idx * lag
        wave = np.sin(phase_i) * amplitude_rad
        joint_angles[idx] = max(0.0, wave)

    angles = np.zeros(5, dtype=float)
    for idx in range(4):
        angles[idx + 1] = angles[idx] + joint_angles[idx]

    raw_x = np.zeros(6, dtype=float)
    raw_z = np.zeros(6, dtype=float)
    for idx in range(5):
        raw_x[idx + 1] = raw_x[idx] + LENGTHS[idx] * np.cos(angles[idx])
        raw_z[idx + 1] = raw_z[idx] + LENGTHS[idx] * np.sin(angles[idx])

    mid_angle = angles[2]
    c_m, s_m = np.cos(-mid_angle), np.sin(-mid_angle)
    flat_x = raw_x * c_m - raw_z * s_m
    flat_z = raw_x * s_m + raw_z * c_m

    mid_center_x = 0.5 * (flat_x[2] + flat_x[3])
    mid_center_z = 0.5 * (flat_z[2] + flat_z[3])
    centered_x = flat_x - mid_center_x
    centered_z = flat_z - mid_center_z

    masses = BASE_MASSES.copy()
    masses[0] += water_l1
    masses[4] += (300.0 - water_l1)

    link_cx = 0.5 * (centered_x[:-1] + centered_x[1:])
    link_cz = 0.5 * (centered_z[:-1] + centered_z[1:])
    total_mass = np.sum(masses)
    com_x = np.sum(masses * link_cx) / total_mass
    com_z = np.sum(masses * link_cz) / total_mass

    pitch_angle_deg = com_x * PITCH_STIFFNESS
    pitch_rad = np.radians(pitch_angle_deg)

    c_p, s_p = np.cos(pitch_rad), np.sin(pitch_rad)

    final_x = centered_x * c_p - centered_z * s_p
    final_z = centered_x * s_p + centered_z * c_p

    final_com_x = com_x * c_p - com_z * s_p
    final_com_z = com_x * s_p + com_z * c_p

    # Final absolute angle of each link in the fluid
    final_angles = angles - mid_angle + pitch_rad

    return final_x, final_z, final_com_x, final_com_z, pitch_angle_deg, final_angles


def solve_hydrodynamic_speed(loc_x, loc_z, angles, prev_x, prev_z, dt):
    """
    Calculates the forward swimming velocity by balancing generated thrust
    from vertical plunging against the tangential drag of the body.
    """
    if prev_x is None:
        return 0.0

    # Convert mm to meters for physics calculations
    x, z = loc_x / 1000.0, loc_z / 1000.0
    px, pz = prev_x / 1000.0, prev_z / 1000.0

    cx, cz = 0.5 * (x[:-1] + x[1:]), 0.5 * (z[:-1] + z[1:])
    pcx, pcz = 0.5 * (px[:-1] + px[1:]), 0.5 * (pz[:-1] + pz[1:])

    # Shape velocity (flapping speed independent of global movement)
    vx_shape = (cx - pcx) / dt
    vz_shape = (cz - pcz) / dt

    L = LENGTHS / 1000.0
    W = WIDTH / 1000.0

    def net_force_x(v_body):
        F_total = 0.0
        for i in range(5):
            theta = angles[i]
            s_t, c_t = np.sin(theta), np.cos(theta)

            # Superimpose global body velocity
            vx = vx_shape[i] + v_body
            vz = vz_shape[i]

            # Resolve velocities into Normal and Tangential components
            vn = vz * c_t - vx * s_t
            vt = vx * c_t + vz * s_t

            # Drag Force Magnitudes
            Fn = -0.5 * RHO * C_N * (L[i] * W) * vn * abs(vn)
            Ft = -0.5 * RHO * C_T * (L[i] * W) * vt * abs(vt)

            # Project drag vectors back to Global X axis
            F_total += (Fn * (-s_t) + Ft * c_t)

        return F_total

    # Bisection search to find steady-state velocity where Net Force = 0
    left, right = -3.0, 3.0
    if net_force_x(left) < 0: return left * 1000.0
    if net_force_x(right) > 0: return right * 1000.0

    for _ in range(50):
        mid = 0.5 * (left + right)
        if net_force_x(mid) > 0:
            left = mid
        else:
            right = mid

    return 0.5 * (left + right) * 1000.0


class CoupledSwimmingSim(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Coupled Hydrodynamics: Pitch, Depth, and Speed")
        self.resize(1500, 950)

        self.phase = 0.0
        self.dt = 0.030
        self.frame_count = 0
        self.global_offset_x = 0.0

        self.prev_x = None
        self.prev_z = None

        self.time_hist = deque(maxlen=200)
        self.tail_z_hist = deque(maxlen=200)
        self.head_z_hist = deque(maxlen=200)
        self.speed_hist = deque(maxlen=200)

        self.init_ui()
        self.timer = QTimer()
        self.timer.timeout.connect(self.update_sim)
        self.timer.start(int(self.dt * 1000))

    def setup_plot(self, plot, title, xlabel, ylabel, invert_y=False):
        label_style = {'color': '#000', 'font-size': '14pt', 'font-weight': 'bold'}
        tick_font = QFont("Arial", 12, QFont.Bold)

        plot.setTitle(title, color="k", size="15pt", bold=True)
        plot.setLabel('bottom', xlabel, **label_style)
        plot.setLabel('left', ylabel, **label_style)

        plot.getAxis("bottom").setTickFont(tick_font)
        plot.getAxis("bottom").setPen(pg.mkPen(color='k', width=2))
        plot.getAxis("left").setTickFont(tick_font)
        plot.getAxis("left").setPen(pg.mkPen(color='k', width=2))
        plot.showGrid(x=True, y=True, alpha=0.4)

        if invert_y:
            plot.getViewBox().invertY(True)

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QHBoxLayout(main_widget)

        plot_layout = QGridLayout()
        pg.setConfigOption("background", "w")
        pg.setConfigOption("foreground", "k")

        # --- Plot 1: Global Geometry ---
        self.plot_geom = pg.PlotWidget()
        self.setup_plot(self.plot_geom, "1. Sagittal Plane (Global Forward Swimming)", "Global Distance X (mm)",
                        "Depth Z (mm)", invert_y=True)
        self.plot_geom.setYRange(-200, 300)

        self.plot_geom.addLine(y=0, pen=pg.mkPen("c", width=3, style=Qt.DashLine))
        self.robot_line = self.plot_geom.plot(pen=pg.mkPen("b", width=8), symbol="o", symbolBrush="b", symbolSize=14)
        self.com_point = self.plot_geom.plot(pen=None, symbol="star", symbolSize=24, symbolBrush="r",
                                             name="Center of Mass")

        # --- Plot 2: Head/Tail Depth ---
        self.plot_depth = pg.PlotWidget()
        self.setup_plot(self.plot_depth, "2. Head & Tail Depth", "Frames", "Depth Z (mm)", invert_y=True)
        self.plot_depth.addLegend(offset=(10, 10))
        self.tail_line = self.plot_depth.plot(pen=pg.mkPen("r", width=4), name="Tail Depth")
        self.head_line = self.plot_depth.plot(pen=pg.mkPen("g", width=4), name="Head Depth")

        # --- Plot 3: Forward Speed ---
        self.plot_speed = pg.PlotWidget()
        self.setup_plot(self.plot_speed, "3. Swimming Speed", "Frames", "Velocity (mm/s)")
        self.speed_line = self.plot_speed.plot(pen=pg.mkPen("m", width=4))

        plot_layout.addWidget(self.plot_geom, 0, 0, 1, 2)
        plot_layout.addWidget(self.plot_depth, 1, 0)
        plot_layout.addWidget(self.plot_speed, 1, 1)
        layout.addLayout(plot_layout, stretch=4)

        # --- UI Controls ---
        control_layout = QVBoxLayout()

        self.info_panel = QLabel("System Status")
        self.info_panel.setStyleSheet(
            "font-size: 16px; font-weight: bold; background-color: #f0f0f0; padding: 15px; border: 2px solid #333; border-radius: 5px;")
        control_layout.addWidget(self.info_panel)

        self.slider_water = self.create_slider("Water in Tail (L1) [g]", 0, 300, 150, control_layout)
        self.label_water_head = QLabel("Water in Head (L5): 150.0 g")
        self.label_water_head.setStyleSheet("font-size: 15px; font-weight: bold; margin-bottom: 25px;")
        control_layout.addWidget(self.label_water_head)

        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        control_layout.addWidget(line)

        # Wave amplitude slider removed here
        self.slider_lag = self.create_slider("Phase Lag", 1, 30, 12, control_layout, scale=0.1)
        self.slider_speed = self.create_slider("Flap Speed", 1, 50, 15, control_layout, scale=0.01)

        control_layout.addStretch()
        layout.addLayout(control_layout, stretch=1)

    def create_slider(self, name, min_val, max_val, init_val, layout, scale=1.0):
        label = QLabel(f"{name}: {init_val * scale:.2f}")
        label.setStyleSheet("font-size: 15px; font-weight: bold; margin-top: 10px;")
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(init_val)

        if "Tail" in name:
            slider.valueChanged.connect(lambda val: label.setText(f"{name}: {val * scale:.1f}"))
            slider.valueChanged.connect(
                lambda val: self.label_water_head.setText(f"Water in Head (L5): {300 - val:.1f} g"))
        else:
            slider.valueChanged.connect(lambda val: label.setText(f"{name}: {val * scale:.2f}"))

        layout.addWidget(label)
        layout.addWidget(slider)
        return slider

    def update_sim(self):
        water_l1 = float(self.slider_water.value())

        # Hardcoded wave amplitude (formerly controlled by the removed slider)
        amp_rad = np.radians(70.0)

        lag = self.slider_lag.value() * 0.1
        speed = self.slider_speed.value() * 0.01

        self.phase -= speed
        self.frame_count += 1

        # 1. Solve the coupled kinematics and pitch
        loc_x, loc_z, com_x, com_z, pitch, angles = solve_floating_kinematics_and_mass(
            self.phase, amp_rad, lag, water_l1
        )

        # 2. Solve fluid dynamics for global forward swimming speed
        body_vel = solve_hydrodynamic_speed(loc_x, loc_z, angles, self.prev_x, self.prev_z, self.dt)
        self.prev_x = loc_x.copy()
        self.prev_z = loc_z.copy()

        # 3. Apply global offset
        self.global_offset_x += body_vel * self.dt
        global_joints_x = loc_x + self.global_offset_x
        global_com_x = com_x + self.global_offset_x

        # Update Plots
        self.robot_line.setData(global_joints_x, loc_z)
        self.com_point.setData([global_com_x], [com_z])
        self.plot_geom.setXRange(global_com_x - 300, global_com_x + 300)

        tail_depth = loc_z[0]
        head_depth = loc_z[-1]

        self.time_hist.append(self.frame_count)
        self.tail_z_hist.append(tail_depth)
        self.head_z_hist.append(head_depth)
        self.speed_hist.append(body_vel)

        self.tail_line.setData(list(self.time_hist), list(self.tail_z_hist))
        self.head_line.setData(list(self.time_hist), list(self.head_z_hist))
        self.speed_line.setData(list(self.time_hist), list(self.speed_hist))

        # Update UI text
        status_text = (
            f"Global Velocity: {body_vel:+.1f} mm/s\n\n"
            f"Hydrostatic Pitch: {pitch:+.2f}°\n"
            f"Tail Depth: {tail_depth:.1f} mm\n"
            f"Head Depth: {head_depth:.1f} mm"
        )
        self.info_panel.setText(status_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = CoupledSwimmingSim()
    window.show()
    sys.exit(app.exec_())