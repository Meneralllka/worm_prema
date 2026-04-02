import sys
import firebase_admin
from firebase_admin import credentials, db
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QSlider, QLabel, QFrame)
from PyQt5.QtCore import Qt

# --- 1. Firebase Configuration ---
# REPLACE THESE WITH YOUR ACTUAL FILE PATH AND URL
CREDENTIALS_FILE = "F:\PREMALab\Mass-Shift\Code\Python\mass-shifter-firebase-adminsdk-fbsvc-5b0d2a409b.json"
DATABASE_URL = "https://mass-shifter-default-rtdb.firebaseio.com/"

try:
    cred = credentials.Certificate(CREDENTIALS_FILE)
    firebase_admin.initialize_app(cred, {
        'databaseURL': DATABASE_URL
    })
    # Create a reference to the specific node in the database
    db_ref = db.reference('robot_params')
    print("Successfully connected to Firebase!")
except Exception as e:
    print(f"Firebase connection failed. Check your JSON path and URL.\nError: {e}")
    sys.exit()


class FirebaseController(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Robot Cloud Controller")
        self.resize(400, 300)

        self.init_ui()
        self.push_initial_state()

    def init_ui(self):
        main_widget = QWidget()
        self.setCentralWidget(main_widget)
        layout = QVBoxLayout(main_widget)

        title = QLabel("Firebase Realtime Controller")
        title.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 20px;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        # --- Power Slider (1.0 to 4.0) ---
        # QSlider only takes integers, so we multiply by 10 (10 to 40)
        self.slider_power, self.label_power = self.create_slider(
            "Sine Power", 10, 40, 20, layout, scale=0.1
        )

        # --- Lag Slider (0.1 to 3.0) ---
        # Multiply by 10 (1 to 30)
        self.slider_lag, self.label_lag = self.create_slider(
            "Phase Lag", 1, 30, 10, layout, scale=0.1
        )

        # --- Amplitude Slider (5 to 90) ---
        self.slider_amp, self.label_amp = self.create_slider(
            "Amplitude [deg]", 5, 90, 45, layout, scale=1.0
        )

        layout.addStretch()

    def create_slider(self, name, min_val, max_val, init_val, layout, scale):
        # UI Label
        label = QLabel(f"{name}: {init_val * scale:.1f}")
        label.setStyleSheet("font-size: 14px; font-weight: bold;")

        # Slider setup
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(init_val)

        # Update the label instantly while dragging
        slider.valueChanged.connect(lambda val: label.setText(f"{name}: {val * scale:.1f}"))

        # Only push to Firebase when the user releases the mouse (saves database quotas)
        slider.sliderReleased.connect(self.update_firebase)

        layout.addWidget(label)
        layout.addWidget(slider)

        # Add a visual separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        layout.addWidget(line)

        return slider, label

    def push_initial_state(self):
        """Pushes the default slider values to Firebase on startup."""
        self.update_firebase()

    def update_firebase(self):
        """Reads all current slider values and sends them to the cloud."""
        power_val = self.slider_power.value() * 0.1
        lag_val = self.slider_lag.value() * 0.1
        amp_val = self.slider_amp.value() * 1.0  # Keep as integer/float

        payload = {
            'power': round(power_val, 1),
            'lag': round(lag_val, 1),
            'amplitude': round(amp_val, 1)
        }

        try:
            db_ref.update(payload)
            print(f"Pushed to Firebase: {payload}")
        except Exception as e:
            print(f"Failed to update Firebase: {e}")


if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = FirebaseController()
    window.show()
    sys.exit(app.exec_())