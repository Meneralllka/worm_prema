import os
import glob
import pandas as pd
import matplotlib.pyplot as plt


def plot_csv_files(input_folder, output_folder):
    """
    Reads all CSV files in the input_folder and saves dual-axis plots
    (Voltage and Current vs TimeStep) to the output_folder.
    """
    # Create output directory if it doesn't exist
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Find all csv files in the specified folder
    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return

    for file_path in csv_files:
        file_name = os.path.basename(file_path)
        print(f"Processing: {file_name}")

        # Load data
        try:
            df = pd.read_csv(file_path)

            # Check if required columns exist
            required_cols = ['TimeStep', 'Voltage_V', 'Current_A']
            if not all(col in df.columns for col in required_cols):
                print(f"Skipping {file_name}: Missing required columns {required_cols}")
                continue

            # Create plot
            fig, ax1 = plt.subplots(figsize=(12, 6))

            # Primary Axis: Voltage
            color_v = 'tab:red'
            ax1.set_xlabel('Time Step')
            ax1.set_ylabel('Voltage (V)', color=color_v)
            ax1.plot(df['TimeStep'], df['Voltage_V'], color=color_v, label='Voltage')
            ax1.tick_params(axis='y', labelcolor=color_v)
            ax1.grid(True, alpha=0.3)

            # Secondary Axis: Current
            ax2 = ax1.twinx()
            color_a = 'tab:blue'
            ax2.set_ylabel('Current (A)', color=color_a)
            ax2.plot(df['TimeStep'], df['Current_A'], color=color_a, label='Current')
            ax2.tick_params(axis='y', labelcolor=color_a)

            plt.title(f"Electrical Data: {file_name}")
            fig.tight_layout()

            # Save the plot
            save_path = os.path.join(output_folder, file_name.replace('.csv', '.png'))
            plt.savefig(save_path)
            plt.close(fig)
            print(f"Saved plot to: {save_path}")

        except Exception as e:
            print(f"Error processing {file_name}: {e}")


if __name__ == "__main__":
    # Specify your folder paths here
    input_dir = 'F:\PREMALab\Mass-Shift\Code\Python\data_logs(100-0)'
    output_dir = 'F:\PREMALab\Mass-Shift\Code\Python\data_logs(100-0)'

    plot_csv_files(input_dir, output_dir)