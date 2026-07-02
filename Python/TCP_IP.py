import sys
import os
import csv
from collections import deque
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QSlider, QLabel, QFrame, QHBoxLayout, QPushButton)
from PyQt5.QtCore import Qt
from PyQt5.QtNetwork import QTcpSocket, QAbstractSocket
import pyqtgraph as pg

# --- TCP/IP Configuration ---
ESP32_IP = "10.236.143.102"
TCP_PORT = 8080


class TCPIPController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Local TCP/IP Controller")
        self.resize(500, 800)

        # Data buffers for the last 100 points
        self.max_points = 100
        self.time_data = deque(maxlen=self.max_points)
        self.voltage_data = deque(maxlen=self.max_points)
        self.current_data = deque(maxlen=self.max_points)

        # --- Low-Pass Filter Variables ---
        self.filter_alpha = 0.8  # Smoothing factor (0.0 to 1.0). Lower = more smooth.
        self.filtered_voltage = None
        self.filtered_current = None

        # Recording state
        self.is_recording = False
        self.csv_file = None
        self.csv_writer = None
        self.log_folder = "data_logs"

        # Initialize network socket
        self.socket = QTcpSocket(self)
        self.socket.readyRead.connect(self.read_tcp_data)
        self.socket.stateChanged.connect(self.connection_state_changed)

        self.init_ui()
        self.connect_to_robot()

    def init_ui(self):
        pg.setConfigOption('background', 'w')
        pg.setConfigOption('foreground', 'k')

        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        # --- Header & Connection Status ---
        title = QLabel("TCP/IP Local Controller")
        title.setStyleSheet("font-size: 18px; font-weight: bold;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        status_layout = QHBoxLayout()
        self.lbl_status = QLabel("Status: Disconnected")
        self.lbl_status.setStyleSheet("color: red; font-weight: bold;")

        self.btn_reconnect = QPushButton("Reconnect")
        self.btn_reconnect.clicked.connect(self.connect_to_robot)

        status_layout.addWidget(self.lbl_status)
        status_layout.addWidget(self.btn_reconnect)
        layout.addLayout(status_layout)

        layout.addWidget(self.create_line())

        # --- Telemetry & Recording Controls ---
        telemetry_layout = QHBoxLayout()
        self.lbl_voltage = QLabel("Voltage: -- V")
        self.lbl_voltage.setStyleSheet("font-size: 16px; color: blue;")

        self.lbl_current = QLabel("Current: -- A")
        self.lbl_current.setStyleSheet("font-size: 16px; color: red;")

        self.btn_record = QPushButton("Start Recording")
        self.btn_record.setStyleSheet("background-color: lightgray; font-weight: bold;")
        self.btn_record.clicked.connect(self.toggle_recording)

        telemetry_layout.addWidget(self.lbl_voltage)
        telemetry_layout.addWidget(self.lbl_current)
        telemetry_layout.addWidget(self.btn_record)
        layout.addLayout(telemetry_layout)

        # --- Telemetry Plots ---
        self.graph_widget = pg.GraphicsLayoutWidget()
        layout.addWidget(self.graph_widget)

        self.plot_v = self.graph_widget.addPlot(title="Voltage (V)")
        self.plot_v.showGrid(x=True, y=True)
        self.plot_v.setLabel('left', 'Voltage', units='V')
        self.plot_v.setLabel('bottom', 'Time', units='ms')
        self.curve_v = self.plot_v.plot(pen=pg.mkPen('b', width=2))

        self.graph_widget.nextRow()

        self.plot_c = self.graph_widget.addPlot(title="Current (A)")
        self.plot_c.showGrid(x=True, y=True)
        self.plot_c.setLabel('left', 'Current', units='A')
        self.plot_c.setLabel('bottom', 'Time', units='ms')
        self.curve_c = self.plot_c.plot(pen=pg.mkPen('r', width=2))

        layout.addWidget(self.create_line())

        # --- Controls ---
        self.slider_freq, self.label_freq = self.create_slider(
            "frequency", "Frequency", 1, 100, 20, layout, scale=0.01
        )
        self.slider_power, self.label_power = self.create_slider(
            "power", "Sine Power", 10, 40, 20, layout, scale=0.1
        )
        self.slider_lag, self.label_lag = self.create_slider(
            "lag", "Phase Lag", 1, 30, 10, layout, scale=0.1
        )
        self.slider_amp, self.label_amp = self.create_slider(
            "amplitude", "Amplitude [deg]", 5, 90, 45, layout, scale=1.0
        )

    def create_line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def create_slider(self, param_key, display_name, min_val, max_val, init_val, layout, scale):
        label = QLabel(f"{display_name}: {init_val * scale:.2f}")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(init_val)

        slider.valueChanged.connect(
            lambda val, n=display_name, s=scale: label.setText(f"{n}: {val * s:.2f}")
        )
        slider.sliderReleased.connect(
            lambda k=param_key, sl=slider, sc=scale: self.send_tcp_update(k, sl.value() * sc)
        )

        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(self.create_line())

        return slider, label

    # --- Recording Functions ---

    def toggle_recording(self):
        if not self.is_recording:
            self.start_recording()
        else:
            self.stop_recording()

    def start_recording(self):
        if not os.path.exists(self.log_folder):
            os.makedirs(self.log_folder)

        freq = self.slider_freq.value() * 0.01
        lag = self.slider_lag.value() * 0.1
        amp = self.slider_amp.value() * 1.0

        existing_files = len([f for f in os.listdir(self.log_folder) if f.endswith('.csv')])
        doc_num = existing_files + 1

        filename = f"{freq:.2f}_{lag:.1f}_{amp:.1f}_{doc_num}.csv"
        filepath = os.path.join(self.log_folder, filename)

        try:
            self.csv_file = open(filepath, mode='w', newline='')
            self.csv_writer = csv.writer(self.csv_file)
            # Updated header to reflect the actual timestamp
            self.csv_writer.writerow(['Timestamp_ms', 'Voltage_V', 'Current_A'])

            self.is_recording = True
            self.btn_record.setText("Stop Recording")
            self.btn_record.setStyleSheet("background-color: red; color: white; font-weight: bold;")
            print(f"Started recording to: {filepath}")
        except Exception as e:
            print(f"Failed to start recording: {e}")

    def stop_recording(self):
        self.is_recording = False
        self.btn_record.setText("Start Recording")
        self.btn_record.setStyleSheet("background-color: lightgray; color: black; font-weight: bold;")

        if self.csv_file:
            self.csv_file.close()
            self.csv_file = None
            self.csv_writer = None
            print("Recording stopped and file saved.")

    def closeEvent(self, event):
        if self.is_recording:
            self.stop_recording()
        event.accept()

    # --- Networking Functions ---

    def connect_to_robot(self):
        if self.socket.state() != QAbstractSocket.ConnectedState:
            self.lbl_status.setText("Status: Connecting...")
            self.lbl_status.setStyleSheet("color: orange; font-weight: bold;")
            self.socket.connectToHost(ESP32_IP, TCP_PORT)

    def connection_state_changed(self, state):
        if state == QAbstractSocket.ConnectedState:
            self.lbl_status.setText("Status: Connected")
            self.lbl_status.setStyleSheet("color: green; font-weight: bold;")
            self.push_initial_state()
        elif state == QAbstractSocket.UnconnectedState:
            self.lbl_status.setText("Status: Disconnected")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
            self.lbl_voltage.setText("Voltage: -- V")
            self.lbl_current.setText("Current: -- A")

            # Reset filters on disconnect so old data doesn't skew new connections
            self.filtered_voltage = None
            self.filtered_current = None

            if self.is_recording:
                self.stop_recording()

    def push_initial_state(self):
        self.send_tcp_update("frequency", self.slider_freq.value() * 0.01)
        self.send_tcp_update("power", self.slider_power.value() * 0.1)
        self.send_tcp_update("lag", self.slider_lag.value() * 0.1)
        self.send_tcp_update("amplitude", self.slider_amp.value() * 1.0)

    def send_tcp_update(self, parameter, value):
        if self.socket.state() == QAbstractSocket.ConnectedState:
            message = f"{parameter}:{round(value, 2)}\n"
            self.socket.write(message.encode('utf-8'))
            print(f"Sent: {message.strip()}")
        else:
            print("Cannot send: Not connected to ESP32")

    def read_tcp_data(self):
        while self.socket.canReadLine():
            try:
                line = self.socket.readLine().data().decode('utf-8').strip()
                if line.startswith("telemetry:"):
                    parts = line.split(":")
                    # Check for 4 parts: "telemetry", "timestamp", "voltage", "current"
                    if len(parts) == 4:
                        timestamp_ms = int(parts[1])
                        raw_voltage = float(parts[2])
                        raw_current = float(parts[3])

                        # --- Apply Low-Pass Filter ---
                        if self.filtered_voltage is None or self.filtered_current is None:
                            # Initialize filter with the first data points
                            self.filtered_voltage = raw_voltage
                            self.filtered_current = raw_current
                        else:
                            # EMA formula: (Alpha * New Value) + ((1 - Alpha) * Previous Filtered Value)
                            self.filtered_voltage = (self.filter_alpha * raw_voltage) + (
                                        (1.0 - self.filter_alpha) * self.filtered_voltage)
                            self.filtered_current = (self.filter_alpha * raw_current) + (
                                        (1.0 - self.filter_alpha) * self.filtered_current)

                        # Update UI with filtered data
                        self.lbl_voltage.setText(f"Voltage: {self.filtered_voltage:.2f} V")
                        self.lbl_current.setText(f"Current: {self.filtered_current:.2f} A")

                        # Use actual ESP32 timestamp instead of counter
                        self.time_data.append(timestamp_ms)
                        self.voltage_data.append(self.filtered_voltage)
                        self.current_data.append(self.filtered_current)

                        self.curve_v.setData(list(self.time_data), list(self.voltage_data))
                        self.curve_c.setData(list(self.time_data), list(self.current_data))

                        # Write filtered data and actual timestamp to CSV
                        if self.is_recording and self.csv_writer:
                            self.csv_writer.writerow(
                                [timestamp_ms, round(self.filtered_voltage, 3), round(self.filtered_current, 3)])

            except Exception as e:
                print(f"Error reading socket data: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TCPIPController()
    window.show()
    sys.exit(app.exec_())