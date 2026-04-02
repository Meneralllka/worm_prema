import serial
import csv
import time

# --- Configuration ---
SERIAL_PORT = 'COM6'  # Update this to your port
BAUD_RATE = 9600
FILE_NAME = "CoT/sensor_data_L22_A40_W0-100.csv"


def main():
    try:
        ser = serial.Serial(SERIAL_PORT, BAUD_RATE, timeout=1)
        time.sleep(2)  # Wait for Arduino reset

        # Record the start time of the script
        start_time = time.time()
        print(f"Logging started. Saving to {FILE_NAME}...")

        with open(FILE_NAME, mode='w', newline='') as file:
            writer = csv.writer(file)
            # CSV Header: Seconds, Voltage, Current
            writer.writerow(["Seconds", "Voltage_V", "Current_A"])

            while True:
                if ser.in_waiting > 0:
                    line = ser.readline().decode('utf-8').strip()

                    try:
                        # Split "Voltage(V):12.00,Current(A):0.50"
                        parts = line.split(',')
                        v_val = float(parts[0].split(':')[1])
                        c_val = float(parts[1].split(':')[1])

                        # Calculate elapsed time in seconds
                        elapsed_seconds = round(time.time() - start_time, 3)

                        # Save only numerical floats
                        writer.writerow([elapsed_seconds, v_val, c_val])
                        file.flush()

                        print(f"Time: {elapsed_seconds}s | V: {v_val} | I: {c_val}")

                    except (IndexError, ValueError):
                        # Ignore malformed lines or headers
                        continue

    except KeyboardInterrupt:
        print("\nLogging stopped.")
    finally:
        if 'ser' in locals() and ser.is_open:
            ser.close()


if __name__ == "__main__":
    main()