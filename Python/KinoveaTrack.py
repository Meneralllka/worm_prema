import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import linregress
import warnings

warnings.filterwarnings('ignore')

# --- Layout Scaling Trick (4x Legend Upscale) ---
title_font = dict(family="Arial, sans-serif", size=20, color="#000000")
axis_font = dict(family="Arial, sans-serif", size=15, color="#000000")
tick_font = dict(family="Arial, sans-serif", size=12, color="#000000")
legend_font = dict(family="Arial, sans-serif", size=22, color="#000000")

# Vibrant Color Scheme
colors = {
    'x_pos': '#023e8a',  # Deep Blue
    'y_pos': '#d00000',  # Strong Red
    'reg': '#000000',  # Black
    'vx': '#2a9d8f',  # Teal Green
    'vy': '#9c6644',  # Earthy Brown
    'v_mag': '#e9c46a',  # Golden Yellow
    'h_mean': '#4cc9f0',  # Cyan (Harmonic Mean)
    'cot_recip': '#f72585',  # Magenta (CoT Reciprocal)
    'path': '#8ab17d',  # Muted Green
    'cot': '#e76f51'  # Burnt Coral
}


def process_and_plot_final():
    datasets = [
        {"file": r"D:\PREMALab\Mass-Shift\Code\Python\WaterVids\Head\all_combined_data_warped.csv", "label": "Head",
         "power": 15.5489},
        {"file": r"D:\PREMALab\Mass-Shift\Code\Python\WaterVids\Mid\all_combined_data_warped.csv", "label": "Mid",
         "power": 14.7613},
        {"file": r"D:\PREMALab\Mass-Shift\Code\Python\WaterVids\Tail\all_combined_data_warped.csv", "label": "Tail",
         "power": 12.8666}
    ]

    mass_kg = 1.204
    g = 9.81
    window_size = 15

    # --- Subplot Setup ---
    fig = make_subplots(
        rows=3, cols=3,
        specs=[
            [{}, {}, {}],
            [{}, {}, {}],
            [{"colspan": 2}, None, {}]
        ],
        subplot_titles=[
            f"Position over Time ({datasets[0]['label']})", f"Position over Time ({datasets[1]['label']})",
            f"Position over Time ({datasets[2]['label']})",
            f"Velocity Components ({datasets[0]['label']})", f"Velocity Components ({datasets[1]['label']})",
            f"Velocity Components ({datasets[2]['label']})",
            "Linear Comparison (Speeds & CoT Reciprocal)", "Log Comparison (Path Dev & CoT)"
        ],
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )

    bar_data = {
        'labels': [],
        'x_vels_m': [], 'x_vels_s': [],
        'mag_vels_m': [], 'mag_vels_s': [],
        'h_mean_m': [], 'h_mean_s': [],
        'cot_recips_m': [], 'cot_recips_s': [],
        'path_deviations_m': [], 'path_deviations_s': [],
        'cots_m': [], 'cots_s': []
    }

    for col_idx, data_info in enumerate(datasets, start=1):
        try:
            df_full = pd.read_csv(data_info["file"], sep=';', decimal=',')
        except FileNotFoundError:
            print(f"Warning: Could not find {data_info['file']}. Skipping.")
            continue

        df_raw = df_full[df_full['Source_File'] != 'AVERAGE_PATH'].copy()

        processed_trials = []
        trial_metrics = {'x_vel': [], 'mag_vel': [], 'h_mean': [], 'path_dev': [], 'cot': [], 'cot_recip': []}

        # --- PROCESS EACH TRIAL INDIVIDUALLY ---
        for source_file, group in df_raw.groupby('Source_File'):
            group = group.sort_values('Time').copy()

            group['X_smooth'] = group['X'].rolling(window=window_size, min_periods=1).mean()
            group['Y_smooth'] = group['Y'].rolling(window=window_size, min_periods=1).mean()

            dt = group['Time'].diff()
            group['Vx'] = group['X_smooth'].diff() / dt
            group['Vy'] = group['Y_smooth'].diff() / dt
            group['V_mag'] = np.sqrt(group['Vx'] ** 2 + group['Vy'] ** 2)

            processed_trials.append(group)

            # Scalar Metrics for Bar Charts
            group_filtered = group[(group['Time'] >= 5) & (group['Time'] <= 15)].copy()
            if len(group_filtered) < 2: continue

            # Regressions
            slope_x, _, _, _, _ = linregress(group_filtered['Time'], group_filtered['X_smooth'])
            slope_y, _, _, _, _ = linregress(group_filtered['Time'], group_filtered['Y_smooth'])

            abs_slope_x = abs(slope_x)
            mag_vel_regression = np.sqrt(slope_x ** 2 + slope_y ** 2)

            # Cost of Transport & Reciprocal
            cot = data_info['power'] / (mass_kg * g * abs_slope_x) if abs_slope_x != 0 else np.nan
            cot_recip = 1.0 / cot if pd.notnull(cot) and cot != 0 else np.nan

            # NEW: Harmonic Mean between X Velocity and CoT Reciprocal
            # Formula for two values: 2ab / (a+b)
            if pd.notnull(cot_recip) and abs_slope_x > 0 and cot_recip > 0:
                h_mean_combined = 2 * (abs_slope_x * cot_recip) / (abs_slope_x + cot_recip)
            else:
                h_mean_combined = np.nan

            # Path Deviation
            step_distances = np.sqrt(group_filtered['X_smooth'].diff() ** 2 + group_filtered['Y_smooth'].diff() ** 2)
            total_path_length = step_distances.sum()
            net_disp = np.sqrt((group_filtered['X_smooth'].iloc[-1] - group_filtered['X_smooth'].iloc[0]) ** 2 +
                               (group_filtered['Y_smooth'].iloc[-1] - group_filtered['Y_smooth'].iloc[0]) ** 2)
            path_deviation = total_path_length / net_disp if net_disp != 0 else 1.0

            trial_metrics['x_vel'].append(abs_slope_x)
            trial_metrics['mag_vel'].append(mag_vel_regression)
            trial_metrics['h_mean'].append(h_mean_combined)
            trial_metrics['path_dev'].append(path_deviation)
            trial_metrics['cot'].append(cot)
            trial_metrics['cot_recip'].append(cot_recip)

        # --- AGGREGATE PER-TRIAL DATA FOR PLOTTING ---
        bar_data['labels'].append(data_info['label'])
        bar_data['x_vels_m'].append(np.nanmean(trial_metrics['x_vel']))
        bar_data['x_vels_s'].append(np.nanstd(trial_metrics['x_vel']))
        bar_data['mag_vels_m'].append(np.nanmean(trial_metrics['mag_vel']))
        bar_data['mag_vels_s'].append(np.nanstd(trial_metrics['mag_vel']))
        bar_data['h_mean_m'].append(np.nanmean(trial_metrics['h_mean']))
        bar_data['h_mean_s'].append(np.nanstd(trial_metrics['h_mean']))
        bar_data['cot_recips_m'].append(np.nanmean(trial_metrics['cot_recip']))
        bar_data['cot_recips_s'].append(np.nanstd(trial_metrics['cot_recip']))
        bar_data['path_deviations_m'].append(np.nanmean(trial_metrics['path_dev']))
        bar_data['path_deviations_s'].append(np.nanstd(trial_metrics['path_dev']))
        bar_data['cots_m'].append(np.nanmean(trial_metrics['cot']))
        bar_data['cots_s'].append(np.nanstd(trial_metrics['cot']))

        # 2. Time-Series Lines (Mean Path Across Trials)
        df_all_trials = pd.concat(processed_trials)
        time_averaged = df_all_trials.groupby('Time').mean(numeric_only=True).reset_index()

        ta_filtered = time_averaged[(time_averaged['Time'] >= 5) & (time_averaged['Time'] <= 20)]
        if len(ta_filtered) > 1:
            mean_slope_x, mean_int_x, _, _, _ = linregress(ta_filtered['Time'], ta_filtered['X_smooth'])
            regression_line_x = mean_slope_x * ta_filtered['Time'] + mean_int_x
        else:
            regression_line_x = pd.Series([np.nan] * len(ta_filtered))

        show_leg = (col_idx == 1)

        # --- ROW 1: Position ---
        fig.add_trace(go.Scatter(
            x=time_averaged['Time'], y=time_averaged['X_smooth'], mode='lines',
            line=dict(color=colors['x_pos'], width=2), opacity=0.8, name='X Position (Mean)',
            legendgroup='pos', showlegend=show_leg
        ), row=1, col=col_idx)

        fig.add_trace(go.Scatter(
            x=time_averaged['Time'], y=time_averaged['Y_smooth'], mode='lines',
            line=dict(color=colors['y_pos'], width=2), opacity=0.8, name='Y Position (Mean)',
            legendgroup='pos', showlegend=show_leg
        ), row=1, col=col_idx)

        fig.add_trace(go.Scatter(
            x=ta_filtered['Time'], y=regression_line_x, mode='lines',
            line=dict(color=colors['reg'], width=1.5, dash='dash'), name='X Regression',
            legendgroup='pos', showlegend=show_leg
        ), row=1, col=col_idx)

        # --- ROW 2: Velocity ---
        fig.add_trace(go.Scatter(
            x=time_averaged['Time'], y=time_averaged['Vx'], mode='lines',
            line=dict(color=colors['vx'], width=1.5), opacity=0.5, name='Vx (Mean)',
            legendgroup='vel', showlegend=show_leg
        ), row=2, col=col_idx)

        fig.add_trace(go.Scatter(
            x=time_averaged['Time'], y=time_averaged['Vy'], mode='lines',
            line=dict(color=colors['vy'], width=1.5), opacity=0.5, name='Vy (Mean)',
            legendgroup='vel', showlegend=show_leg
        ), row=2, col=col_idx)

        fig.add_trace(go.Scatter(
            x=time_averaged['Time'], y=time_averaged['V_mag'], mode='lines',
            line=dict(color=colors['v_mag'], width=2), opacity=0.9, name='Magnitude Vel (Mean)',
            legendgroup='vel', showlegend=show_leg
        ), row=2, col=col_idx)

    # --- ROW 3: Bar Charts ---
    contour_style = dict(color='black', width=1)
    error_style = dict(type='data', color='black', thickness=1.5)

    fig.add_trace(go.Bar(
        x=bar_data['labels'], y=bar_data['x_vels_m'], name='Reg Vx',
        marker=dict(color=colors['vx'], line=contour_style), offsetgroup=1,
        error_y=dict(**error_style, array=bar_data['x_vels_s'])
    ), row=3, col=1)

    fig.add_trace(go.Bar(
        x=bar_data['labels'], y=bar_data['mag_vels_m'], name='Reg V_mag',
        marker=dict(color=colors['v_mag'], line=contour_style), offsetgroup=2,
        error_y=dict(**error_style, array=bar_data['mag_vels_s'])
    ), row=3, col=1)

    fig.add_trace(go.Bar(
        x=bar_data['labels'], y=bar_data['h_mean_m'], name='Harmonic Mean (Vx & 1/CoT)',
        marker=dict(color=colors['h_mean'], line=contour_style), offsetgroup=3,
        error_y=dict(**error_style, array=bar_data['h_mean_s'])
    ), row=3, col=1)

    fig.add_trace(go.Bar(
        x=bar_data['labels'], y=bar_data['cot_recips_m'], name='CoT Reciprocal (1/CoT)',
        marker=dict(color=colors['cot_recip'], line=contour_style), offsetgroup=4,
        error_y=dict(**error_style, array=bar_data['cot_recips_s'])
    ), row=3, col=1)

    fig.add_trace(go.Bar(
        x=bar_data['labels'], y=bar_data['path_deviations_m'], name='Path Deviation',
        marker=dict(color=colors['path'], line=contour_style), offsetgroup=1,
        error_y=dict(**error_style, array=bar_data['path_deviations_s'])
    ), row=3, col=3)

    fig.add_trace(go.Bar(
        x=bar_data['labels'], y=bar_data['cots_m'], name='Relative COT',
        marker=dict(color=colors['cot'], line=contour_style), offsetgroup=2,
        error_y=dict(**error_style, array=bar_data['cots_s'])
    ), row=3, col=3)

    # --- Global Layout Styling ---
    fig.update_layout(
        height=1125, width=1500,
        plot_bgcolor='white', paper_bgcolor='white',
        barmode='group',
        showlegend=True,
        legend=dict(
            font=legend_font, orientation="h", yanchor="bottom", y=1.03,
            xanchor="center", x=0.5, bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="black", borderwidth=1.5,
            itemsizing="constant", itemwidth=40
        ),
        margin=dict(l=100, r=100, t=150, b=100)
    )

    for annotation in fig['layout']['annotations']:
        annotation['font'] = title_font

    # --- Systematic Axis Styling ---
    for r in [1, 2, 3]:
        for c in [1, 2, 3]:
            if r == 3 and c == 2:
                continue

            if r == 1:
                y_title = "Position (px)"
            elif r == 2:
                y_title = "Velocity (px/s)"
            elif r == 3 and c == 1:
                y_title = "Linear Metrics"
            elif r == 3 and c == 3:
                y_title = "Log Metrics"

            fig.update_yaxes(
                title=dict(text=y_title, font=axis_font),
                showgrid=True, gridcolor='lightgray', gridwidth=1,
                zeroline=True, zerolinecolor='black', zerolinewidth=1.5,
                tickfont=tick_font, row=r, col=c
            )

            x_title = "Time (s)" if r < 3 else "Configuration"
            fig.update_xaxes(
                title=dict(text=x_title, font=axis_font),
                showgrid=True, gridcolor='lightgray', gridwidth=1,
                zeroline=True, zerolinecolor='black', zerolinewidth=1.5,
                tickfont=tick_font, row=r, col=c
            )

            if r == 1:
                fig.update_yaxes(autorange="reversed", row=r, col=c)

            if r == 3 and c == 3:
                fig.update_yaxes(type="log", row=r, col=c)

    # Output exports
    fig.write_html("comprehensive_kinematics.html")

    try:
        fig.write_image("comprehensive_kinematics.png", scale=4)
        print("Exported: comprehensive_kinematics.png (6000x4500 pixels with 4x Legend)")
    except ValueError:
        print("Exported: comprehensive_kinematics.html. To export PNG, run: pip install -U kaleido")


if __name__ == "__main__":
    process_and_plot_final()
"""
import os
import glob
import pandas as pd
import numpy as np


def process_tracking_data(directory_path):
    # Search for all CSV files in the given directory
    # Ignores any previously generated "all_combined_data" file to prevent duplicates
    search_pattern = os.path.join(directory_path, '*.csv')
    csv_files = [f for f in glob.glob(search_pattern) if 'all_combined_data' not in os.path.basename(f)]

    if not csv_files:
        print(f"No valid CSV files found in directory: {directory_path}")
        return

    all_dataframes = []

    for file in csv_files:
        try:
            # Read the CSV (handling semicolon separators and comma decimals)
            df = pd.read_csv(file, sep=';', decimal=',')

            # Assuming columns are always [Time, X, Y]
            time_col = df.columns[0]
            x_col = df.columns[1]
            y_col = df.columns[2]

            # Calculate the differences between consecutive rows
            dt = df[time_col].diff()
            dx = df[x_col].diff()
            dy = df[y_col].diff()

            # Calculate velocities
            df['Velocity_X'] = dx / dt
            df['Velocity_Y'] = dy / dt
            df['Velocity_Magnitude'] = np.sqrt(df['Velocity_X'] ** 2 + df['Velocity_Y'] ** 2)

            # Fill the NaN values in the first row with 0
            df.fillna(0, inplace=True)

            # Add identifying columns
            df['Source_File'] = os.path.basename(file)

            # Rename coordinates to standard names for easy combining
            df.rename(columns={time_col: 'Time', x_col: 'X', y_col: 'Y'}, inplace=True)

            # Make sure Time is rounded slightly to allow clean grouping across files later
            df['Time'] = df['Time'].round(4)

            all_dataframes.append(df)
            print(f"Processed: {os.path.basename(file)}")

        except Exception as e:
            print(f"Error processing {file}: {e}")

    if not all_dataframes:
        print("No data could be processed.")
        return

    # Combine all individual files into one DataFrame
    combined_df = pd.concat(all_dataframes, ignore_index=True)

    # Calculate the Average Path by grouping by Time
    print("\nCalculating average path...")
    average_path_df = combined_df.groupby('Time')[
        ['X', 'Y', 'Velocity_X', 'Velocity_Y', 'Velocity_Magnitude']].mean().reset_index()

    # Label these average rows so they can exist in the same file
    average_path_df['Source_File'] = 'AVERAGE_PATH'

    # Append the average path data to the bottom of the combined data
    final_df = pd.concat([combined_df, average_path_df], ignore_index=True)

    # Save the single master file back to the same directory
    output_filepath = os.path.join(directory_path, 'all_combined_data.csv')

    # Save using the same European format (sep=';', decimal=',')
    final_df.to_csv(output_filepath, index=False, sep=';', decimal=',')

    print(f"\nSUCCESS: All data (including averages) saved to '{output_filepath}'")


# ==========================================
# HOW TO USE THE SCRIPT:
# Put your folder path inside the quotes below
# ==========================================
YOUR_DIRECTORY_ADDRESS = "D:\\PREMALab\\Mass-Shift\\Code\\Python\\WaterVids\\Head"  # Replace with your folder path, e.g., "C:/Users/Data/Trajectories"

process_tracking_data(YOUR_DIRECTORY_ADDRESS)"""