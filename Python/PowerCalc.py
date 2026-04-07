import os
import glob
import pandas as pd


def calculate_average_power(input_folder, summary_output_file):
    """
    Calculates the average power consumption (Watts) for each CSV in a folder.
    """
    results = []

    # Find all csv files in the specified folder
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return

    for file_path in csv_files:
        file_name = os.path.basename(file_path)

        try:
            df = pd.read_csv(file_path)

            # Ensure required columns exist
            if 'Voltage_V' in df.columns and 'Current_A' in df.columns:
                # Calculate instantaneous power (W)
                # Power = Voltage * Current
                df['Power_W'] = df['Voltage_V'] * df['Current_A']

                # Average Power is the mean of all power readings
                avg_power = df['Power_W'].mean()

                results.append({
                    'filename': file_name,
                    'average_power_watts': round(avg_power, 4)
                })
                print(f"Processed {file_name}: {avg_power:.4f} W")
            else:
                print(f"Skipping {file_name}: Required columns missing.")

        except Exception as e:
            print(f"Error processing {file_name}: {e}")

    # Create the summary CSV
    summary_df = pd.DataFrame(results)
    summary_df.to_csv(summary_output_file, index=False)
    print(f"\nSummary report saved to: {summary_output_file}")


if __name__ == "__main__":
    # Update these paths to your actual folder locations
    input_dir = 'F:\PREMALab\Mass-Shift\Code\Python\data_logs(0-100)'
    output_csv = 'F:\PREMALab\Mass-Shift\Code\Python\data_logs(0-100)\\average_power_summary.csv'

    calculate_average_power(input_dir, output_csv)