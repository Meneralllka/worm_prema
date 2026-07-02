import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors as pc

# --- Font Rules (Consistent with your robot code) ---
title_font  = dict(family="Arial, sans-serif", size=80, color="#000000")
axis_font   = dict(family="Arial, sans-serif", size=60, color="#000000")
tick_font   = dict(family="Arial, sans-serif", size=48, color="#000000")
legend_font = dict(family="Arial, sans-serif", size=60, color="#000000")

def generate_3x3_comparison():
    datasets = [
        {"file": "TankVids/Head.csv", "label": "Head"},
        {"file": "TankVids/Mid.csv", "label": "Mid"},
        {"file": "TankVids/Tail.csv", "label": "Tail"}
    ]

    # Subplot titles for the 3x3 grid
    subplot_titles = [
        f"Global Form ({datasets[0]['label']})", f"Global Form ({datasets[1]['label']})", f"Global Form ({datasets[2]['label']})",
        f"Relative Form ({datasets[0]['label']})", f"Relative Form ({datasets[1]['label']})", f"Relative Form ({datasets[2]['label']})",
        f"Trajectories ({datasets[0]['label']})", f"Trajectories ({datasets[1]['label']})", f"Trajectories ({datasets[2]['label']})"
    ]

    fig = make_subplots(
        rows=3, cols=3,
        subplot_titles=subplot_titles,
        vertical_spacing=0.1,
        horizontal_spacing=0.05
    )

    for col_idx, data_info in enumerate(datasets, start=1):
        try:
            df = pd.read_csv(data_info["file"])
        except FileNotFoundError:
            print(f"Warning: Could not find {data_info['file']}. Skipping column {col_idx}.")
            continue

        # --- MODIFICATION: Filter IDs and Normalize Y ---
        # 1. Keep only IDs 0, 1, 2, and 3
        df = df[df['ID'].isin([0, 1, 2, 3])]

        # 2. Find the lowest Y point for each ID and make it 0
        for obj_id in df['ID'].unique():
            min_y = df.loc[df['ID'] == obj_id, 'Center_Y'].min()
            df.loc[df['ID'] == obj_id, 'Center_Y'] -= min_y
        # ------------------------------------------------

        # --- PREP DATA FOR ROWS 1 & 2 (Waveforms) ---
        unique_frames = df['Frame'].unique()
        target_poses = 40 # Reduced slightly for 3x3 clarity
        frame_step = max(1, len(unique_frames) // target_poses)
        frames_to_plot = unique_frames[::frame_step]

        # Color gradient for time (Viridis)
        viridis_colors = pc.sample_colorscale('Viridis', [i / max(1, len(frames_to_plot) - 1) for i in range(len(frames_to_plot))])

        for idx, frame_num in enumerate(frames_to_plot):
            frame_data = df[df['Frame'] == frame_num].sort_values(by='ID')
            if len(frame_data) > 1:
                show_leg_wave = (idx == 0 and col_idx == 1)

                # Row 1: Global Form
                fig.add_trace(go.Scatter(
                    x=frame_data['Center_X'], y=frame_data['Center_Y'],
                    mode='lines+markers', line=dict(color=viridis_colors[idx], width=6),
                    marker=dict(size=12), opacity=0.5, name='Waveform Pose',
                    legendgroup='wave', showlegend=show_leg_wave
                ), row=1, col=col_idx)

                # Row 2: Relative Form
                anchor = frame_data[frame_data['ID'] == 0]
                if anchor.empty: anchor = frame_data.iloc[0:1]

                rel_x = frame_data['Center_X'] - anchor['Center_X'].values[0]
                rel_y = frame_data['Center_Y'] - anchor['Center_Y'].values[0]

                fig.add_trace(go.Scatter(
                    x=rel_x, y=rel_y,
                    mode='lines+markers', line=dict(color=viridis_colors[idx], width=6),
                    marker=dict(size=12), opacity=0.5, name='Relative Pose',
                    legendgroup='rel_wave', showlegend=False
                ), row=2, col=col_idx)

        # --- PREP DATA FOR ROW 3 (Trajectories) ---
        unique_ids = df['ID'].unique()
        # Color per ID (Plotly3)
        id_colors = pc.sample_colorscale('Plotly3', [i / max(1, len(unique_ids) - 1) for i in range(len(unique_ids))])

        for i, obj_id in enumerate(unique_ids):
            obj_data = df[df['ID'] == obj_id].sort_values(by='Frame')
            show_leg_traj = (col_idx == 1)

            fig.add_trace(go.Scatter(
                x=obj_data['Center_X'], y=obj_data['Center_Y'],
                mode='lines+markers', line=dict(color=id_colors[i], width=8),
                marker=dict(size=15), opacity=0.8, name=f'ID {obj_id} Path',
                legendgroup=f'id_{obj_id}', showlegend=show_leg_traj
            ), row=3, col=col_idx)

    # --- Global Layout Styling ---
    fig.update_layout(
        height=4500, width=6000,
        plot_bgcolor='white', paper_bgcolor='white',
        showlegend=True,
        legend=dict(
            font=legend_font, orientation="h", yanchor="bottom", y=1.04,
            xanchor="center", x=0.5, bgcolor="rgba(255, 255, 255, 0.9)",
            bordercolor="black", borderwidth=6
        ),
        margin=dict(l=200, r=200, t=400, b=200)
    )

    for annotation in fig['layout']['annotations']:
        annotation['font'] = title_font

    # --- Systematic Axis Styling ---
    for r in [1, 2, 3]:
        for c in [1, 2, 3]:
            # Reversed Y for OpenCV and fixed aspect ratio
            fig.update_yaxes(
                title=dict(text="Y Position (px)", font=axis_font),
                autorange="reversed", scaleanchor=f"x{c + (r-1)*3}" if (c + (r-1)*3) > 1 else "x",
                scaleratio=1, showgrid=True, gridcolor='lightgray', gridwidth=3,
                zeroline=True, zerolinecolor='black', zerolinewidth=6,
                tickfont=tick_font, row=r, col=c
            )
            fig.update_xaxes(
                title=dict(text="X Position (px)", font=axis_font),
                showgrid=True, gridcolor='lightgray', gridwidth=3,
                zeroline=True, zerolinecolor='black', zerolinewidth=6,
                tickfont=tick_font, row=r, col=c
            )

    fig.write_html("full_analysis_3x3.html")
    fig.write_image("Tank_full_analysis_3x3.svg", scale=1)
    print("Exported: full_analysis_3x3.html")

if __name__ == "__main__":
    generate_3x3_comparison()