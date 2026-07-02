import os
import glob
import pandas as pd


def calculate_average_power(input_folder, summary_output_file):
    """
    Calculates the average power consumption (Watts) for each CSV in a folder.
    Automatically finds the idle offset, filters noise, and calculates ground-truth power.
    """
    results = []
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return

    for file_path in csv_files:
        file_name = os.path.basename(file_path)

        try:
            df = pd.read_csv(file_path)

            if 'Voltage_V' in df.columns and 'Current_A' in df.columns:

                # --- 1. OFFSET CALIBRATION ---
                # Find the 50-timestep window where the current fluctuates the least (the robot isn't moving)
                # We use variance to find the most stable continuous chunk of data.
                rolling_variance = df['Current_A'].rolling(window=50).var()
                stable_end_idx = rolling_variance.idxmin()

                # The mean of this highly stable window is our true zero-current offset
                baseline_offset = df['Current_A'].loc[stable_end_idx - 49: stable_end_idx].mean()

                # --- 2. ADJUST CURRENT ---
                # Subtract the offset so the idle state becomes exactly 0 Amps
                df['Adjusted_Current_A'] = df['Current_A'] - baseline_offset

                # --- 3. APPLY FILTERS ---
                # Apply a moving average filter to smooth out ACS712 high-frequency noise
                df['Filtered_Current_A'] = df['Adjusted_Current_A'].rolling(window=10, min_periods=1).mean()

                # Clip out impossible physical values (no negative voltage, no negative current)
                # This prevents baseline noise from generating "negative power"
                df['Filtered_Current_A'] = df['Filtered_Current_A'].clip(lower=0)
                df['Filtered_Voltage_V'] = df['Voltage_V'].clip(lower=0)

                # --- 4. CALCULATE POWER ---
                # Calculate instantaneous power (W)
                df['Power_W'] = df['Filtered_Voltage_V'] * df['Filtered_Current_A']

                # Average Power is the mean of all valid power readings
                avg_power = df['Power_W'].mean()

                results.append({
                    'filename': file_name,
                    'calibrated_offset_A': round(baseline_offset, 6),
                    'average_power_watts': round(avg_power, 4)
                })
                print(f"Processed {file_name}: Offset={baseline_offset:.6f} A, Avg Power={avg_power:.4f} W")

                # OPTIONAL: Save the cleaned and filtered data back to a new CSV for plotting
                # cleaned_file_path = os.path.join(input_folder, f"cleaned_{file_name}")
                # df.to_csv(cleaned_file_path, index=False)

            else:
                print(f"Skipping {file_name}: Required columns missing.")

        except Exception as e:
            print(f"Error processing {file_name}: {e}")

    # Create the summary CSV
    if results:
        summary_df = pd.DataFrame(results)
        summary_df.to_csv(summary_output_file, index=False)
        print(f"\nSummary report saved to: {summary_output_file}")
    else:
        print("No data processed to save.")


if __name__ == "__main__":
    # Note: Using raw strings (r'') for Windows paths to avoid escape character issues
    input_dir = r'D:\PREMALab\Mass-Shift\Code\Python\data_logs'
    output_csv = r'D:\PREMALab\Mass-Shift\Code\Python\data_logs\average_power_summary.csv'

    calculate_average_power(input_dir, output_csv)