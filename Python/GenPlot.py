import os
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def generate_all_plotly_pngs():
    input_dir = "robot_sim_data"
    output_dir = "robot_sim_plots_png"

    # Create the output directory
    os.makedirs(output_dir, exist_ok=True)

    # Gather files
    try:
        files = [f for f in os.listdir(input_dir) if f.endswith('.csv')]
    except FileNotFoundError:
        print(f"Error: Directory '{input_dir}' not found.")
        return

    total_files = len(files)
    if total_files == 0:
        print("No CSV files found.")
        return

    print(f"Generating {total_files} high-resolution PNGs via Plotly...\n")

    for idx, filename in enumerate(files):
        filepath = os.path.join(input_dir, filename)

        # 1. Load Data (Using Pandas for speed and header mapping)
        # Assuming columns: [index, time, local_x, local_y, disp_x, vel_raw]
        df = pd.read_csv(filepath)
        cols = df.columns

        # 2. Smooth Velocity (5-frame window)
        df['vel_smooth'] = df[cols[5]].rolling(window=5, center=True).mean()

        # 3. Create Figure (1x3 Grid)
        fig = make_subplots(
            rows=1, cols=3,
            subplot_titles=("Local CoM Trajectory", "Global X Displacement", "Linear Velocity"),
            horizontal_spacing=0.08
        )

        # --- Plot 1: Trajectory ---
        fig.add_trace(
            go.Scatter(x=df[cols[2]], y=df[cols[3]], mode='lines',
                       line=dict(color='#E74C3C', width=2), name="Trajectory"),
            row=1, col=1
        )

        # --- Plot 2: Displacement ---
        fig.add_trace(
            go.Scatter(x=df[cols[1]], y=df[cols[4]], mode='lines',
                       line=dict(color='#27AE60', width=2), name="Displacement"),
            row=1, col=2
        )

        # --- Plot 3: Velocity (Raw + Smooth) ---
        # Raw (Faded)
        fig.add_trace(
            go.Scatter(x=df[cols[1]], y=df[cols[5]], mode='lines',
                       line=dict(color='#9B59B6', width=1), opacity=0.3, name="Raw"),
            row=1, col=3
        )
        # Smoothed (Bold)
        fig.add_trace(
            go.Scatter(x=df[cols[1]], y=df['vel_smooth'], mode='lines',
                       line=dict(color='#8E44AD', width=2.5), name="Smoothed"),
            row=1, col=3
        )

        # 4. Design & Layout Styling
        title_clean = filename.replace('sim_', '').replace('.csv', '').replace('_', ' | ')

        fig.update_layout(
            title=dict(text=f"Robot Simulation: {title_clean}", x=0.5, font=dict(size=18)),
            template="plotly_white",  # The "Design" choice
            showlegend=False,
            height=500,
            width=1600,
            margin=dict(t=100, b=50, l=50, r=50)
        )

        # Maintain physical aspect ratio for the trajectory plot
        fig.update_yaxes(scaleanchor="x", scaleratio=1, row=1, col=1)

        # Add labels manually for subplots (Plotly subplots handle titles, but we want axes labels)
        fig.update_xaxes(title_text="Local X (mm)", row=1, col=1)
        fig.update_yaxes(title_text="Local Y (mm)", row=1, col=1)
        fig.update_xaxes(title_text="Time (s)", row=1, col=2)
        fig.update_yaxes(title_text="Distance (mm)", row=1, col=2)
        fig.update_xaxes(title_text="Time (s)", row=1, col=3)
        fig.update_yaxes(title_text="Velocity (mm/s)", row=1, col=3)

        # 5. Save as PNG
        # scale=2 ensures the text and lines are ultra-crisp
        out_name = filename.replace('.csv', '.png')
        fig.write_image(os.path.join(output_dir, out_name), engine="kaleido", scale=2)

        # Progress tracker
        if (idx + 1) % 50 == 0 or (idx + 1) == total_files:
            print(f"Finished {idx + 1}/{total_files} plots...")

    print(f"\nSuccess! All PNGs are located in: {output_dir}")


if __name__ == "__main__":
    generate_all_plotly_pngs()