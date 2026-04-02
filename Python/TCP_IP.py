import sys
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QSlider, QLabel, QFrame, QHBoxLayout, QPushButton)
from PyQt5.QtCore import Qt
from PyQt5.QtNetwork import QTcpSocket, QAbstractSocket

# --- TCP/IP Configuration ---
ESP32_IP = "10.213.8.189"
TCP_PORT = 8080


class TCPIPController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Local TCP/IP Controller")
        self.resize(450, 400)

        # Initialize network socket
        self.socket = QTcpSocket(self)
        self.socket.readyRead.connect(self.read_tcp_data)
        self.socket.stateChanged.connect(self.connection_state_changed)

        self.init_ui()
        self.connect_to_robot()

    def init_ui(self):
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

        # Separator
        layout.addWidget(self.create_line())

        # --- Telemetry Display ---
        telemetry_layout = QHBoxLayout()
        self.lbl_voltage = QLabel("Voltage: -- V")
        self.lbl_voltage.setStyleSheet("font-size: 16px; color: blue;")

        self.lbl_current = QLabel("Current: -- A")
        self.lbl_current.setStyleSheet("font-size: 16px; color: red;")

        telemetry_layout.addWidget(self.lbl_voltage)
        telemetry_layout.addWidget(self.lbl_current)
        layout.addLayout(telemetry_layout)

        layout.addWidget(self.create_line())

        # --- Controls ---
        self.slider_power, self.label_power = self.create_slider(
            "power", "Sine Power", 10, 40, 20, layout, scale=0.1
        )
        self.slider_lag, self.label_lag = self.create_slider(
            "lag", "Phase Lag", 1, 30, 10, layout, scale=0.1
        )
        self.slider_amp, self.label_amp = self.create_slider(
            "amplitude", "Amplitude [deg]", 5, 90, 45, layout, scale=1.0
        )

        layout.addStretch()

    def create_line(self):
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        return line

    def create_slider(self, param_key, display_name, min_val, max_val, init_val, layout, scale):
        label = QLabel(f"{display_name}: {init_val * scale:.1f}")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")

        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(init_val)

        slider.valueChanged.connect(
            lambda val, n=display_name, s=scale: label.setText(f"{n}: {val * s:.1f}")
        )
        slider.sliderReleased.connect(
            lambda k=param_key, sl=slider, sc=scale: self.send_tcp_update(k, sl.value() * sc)
        )

        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(self.create_line())

        return slider, label

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
            self.push_initial_state()  # Push slider values once connected
        elif state == QAbstractSocket.UnconnectedState:
            self.lbl_status.setText("Status: Disconnected")
            self.lbl_status.setStyleSheet("color: red; font-weight: bold;")
            self.lbl_voltage.setText("Voltage: -- V")
            self.lbl_current.setText("Current: -- A")

    def push_initial_state(self):
        self.send_tcp_update("power", self.slider_power.value() * 0.1)
        self.send_tcp_update("lag", self.slider_lag.value() * 0.1)
        self.send_tcp_update("amplitude", self.slider_amp.value() * 1.0)

    def send_tcp_update(self, parameter, value):
        if self.socket.state() == QAbstractSocket.ConnectedState:
            message = f"{parameter}:{round(value, 1)}\n"
            self.socket.write(message.encode('utf-8'))
            print(f"Sent: {message.strip()}")
        else:
            print("Cannot send: Not connected to ESP32")

    def read_tcp_data(self):
        """Triggered automatically whenever the ESP32 sends data."""
        while self.socket.canReadLine():
            try:
                line = self.socket.readLine().data().decode('utf-8').strip()
                # Parse the incoming telemetry string
                if line.startswith("telemetry:"):
                    parts = line.split(":")
                    if len(parts) == 3:
                        voltage = float(parts[1])
                        current = float(parts[2])

                        # Update the GUI labels
                        self.lbl_voltage.setText(f"Voltage: {voltage:.2f} V")
                        self.lbl_current.setText(f"Current: {current:.2f} A")
            except Exception as e:
                print(f"Error reading socket data: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = TCPIPController()
    window.show()
    sys.exit(app.exec_())