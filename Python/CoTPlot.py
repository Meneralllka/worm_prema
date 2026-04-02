import pandas as pd
import numpy as np
import glob
import os
import re
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# --- Configuration ---
INPUT_FOLDER = "CoT_cropped_data/"
RAW_EXP_PATH = "F:\PREMALab\Mass-Shift\Experiments\Data\RawExp.csv"
G = 9.81
MASS = 1.0  # kg (Update if known)
WINDOW_SECONDS = 3.0
WATER_RATIOS = ["0-100", "50-50", "100-0"]
AMPLITUDES = [10, 40, 70, 90]  # Ensuring 70 is in the range for blank space


def calculate_all_metrics():
    # 1. Load Velocity Data
    try:
        raw_df = pd.read_csv(RAW_EXP_PATH)
        raw_df['Lag_val'] = raw_df['Lag'].str.replace(',', '.').astype(float)
        raw_df['Vel_val'] = raw_df['Vel (cm/s)'].str.replace(',', '.').astype(float) / 100.0
    except Exception as e:
        print(f"Error loading RawExp.csv: {e}")
        return None

    results = []

    # 2. Process Sensor Files
    files = glob.glob(os.path.join(INPUT_FOLDER, "*.csv"))
    if not files:
        print(f"No files found in {INPUT_FOLDER}")
        return None

    for file in files:
        filename = os.path.basename(file)
        # Extract L, A, W
        match = re.search(r'L(\d)(\d)_A(\d+)_W(\d+-\d+)', filename)
        if not match: continue

        lag = float(f"{match.group(1)}.{match.group(2)}")
        amp = int(match.group(3))
        water = match.group(4)
        w_match = f"({water.split('-')[0]}, {water.split('-')[1]})"

        # Match velocity
        row = raw_df[(np.isclose(raw_df['Lag_val'], lag)) &
                     (raw_df['Amplitude'] == amp) &
                     (raw_df['Water (H, T)'] == w_match)]

        if row.empty: continue
        vel = row.iloc[0]['Vel_val']

        # Calculate Mean Power (3s)
        df_s = pd.read_csv(file)
        df_win = df_s[df_s['Seconds'] <= WINDOW_SECONDS]
        power = (df_win['Voltage_V'] * df_win['Current_A']).mean()

        # Metrics
        cot = power / (MASS * G * vel) if vel > 0 else np.nan
        # Harmonic Mean of Velocity and 1/CoT
        # HM = 2 / ( (1/v) + (1/(1/CoT)) ) = 2 / (1/v + CoT)
        h_mean = 2 / ((1 / vel) + cot) if (vel > 0 and cot > 0) else np.nan

        results.append({
            'Lag': lag, 'Amplitude': amp, 'Water': water,
            'Velocity': vel, 'CoT': cot, 'H_Mean': h_mean
        })

    return pd.DataFrame(results)


# --- 3. Plotting Logic ---
df = calculate_all_metrics()

if df is not None:
    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=[f"{m} - {w}" for m in ["Velocity", "CoT", "H-Mean"] for w in WATER_RATIOS],
        horizontal_spacing=0.08, vertical_spacing=0.1
    )

    metrics = ['Velocity', 'CoT', 'H_Mean']

    for row, metric in enumerate(metrics, start=1):
        for col, water in enumerate(WATER_RATIOS, start=1):
            # Pivot data for heatmap
            subset = df[df['Water'] == water]
            pivot = subset.pivot_table(index='Lag', columns='Amplitude', values=metric, aggfunc='mean')

            # Ensure all amplitudes (including 70) exist in the columns to force the gap
            for a in AMPLITUDES:
                if a not in pivot.columns:
                    pivot[a] = np.nan
            pivot = pivot.reindex(columns=sorted(pivot.columns))

            fig.add_trace(
                go.Heatmap(
                    z=pivot.values,
                    x=pivot.columns,
                    y=pivot.index,
                    coloraxis="coloraxis" + str(row),  # Different scales per row
                    text=np.round(pivot.values, 3),
                    texttemplate="%{text}",
                    hoverongaps=False
                ),
                row=row, col=col
            )

    # Styling
    # Styling - Corrected coloraxis title placement
    fig.update_layout(
        title_text="Multi-Metric Robot Performance Analysis",
        height=1000,
        width=1200,
        coloraxis1=dict(
            colorscale='Viridis',
            colorbar=dict(x=1.0, y=0.85, len=0.25, title="Vel (m/s)")
        ),
        coloraxis2=dict(
            colorscale='Reds_r',
            colorbar=dict(x=1.0, y=0.5, len=0.25, title="CoT")
        ),
        coloraxis3=dict(
            colorscale='Cividis',
            colorbar=dict(x=1.0, y=0.15, len=0.25, title="H-Mean")
        ),
        showlegend=False
    )

    fig.update_xaxes(title_text="Amplitude (deg)")
    fig.update_yaxes(title_text="Lag (s)")

    fig.write_html("Performance_Analysis_Heatmaps.html")
    fig.write_image("Performance_Analysis_Heatmaps.png")
    print("Success! Visualization generated.")