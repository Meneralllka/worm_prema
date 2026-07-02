import os
import glob
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.ndimage import gaussian_filter1d
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SETUP & AESTHETICS (Liquid Glass Theme)
# ==========================================
ordered_cats = ['head', 'mid', 'tail', 'ht', 'th']
cat_labels = {
    'head': 'Head Heavy',
    'mid': 'Balanced',
    'tail': 'Tail Heavy',
    'ht': 'Head-Tail',
    'th': 'Tail-Head'
}

# High-saturation, high-opacity colors
colors = {
    'head': {'rgba': 'rgba(225, 63, 41, 0.95)', 'pale': 'rgba(225, 63, 41, 0.35)'},  # Red
    'mid': {'rgba': 'rgba(0, 107, 204, 0.95)', 'pale': 'rgba(0, 107, 204, 0.35)'},  # Blue
    'tail': {'rgba': 'rgba(142, 68, 173, 0.95)', 'pale': 'rgba(142, 68, 173, 0.35)'},  # Purple
    'ht': {'rgba': 'rgba(46, 204, 113, 0.95)', 'pale': 'rgba(46, 204, 113, 0.35)'},  # Green
    'th': {'rgba': 'rgba(241, 196, 15, 0.95)', 'pale': 'rgba(241, 196, 15, 0.35)'}  # Yellow
}

# Typography strictly limited to black Arial
font_title = dict(family="Arial Black, Arial, sans-serif", size=26, color="black")
font_axis = dict(family="Arial, sans-serif", size=22, color="black")
font_tick = dict(family="Arial, sans-serif", size=16, color="black")
font_legend = dict(family="Arial, sans-serif", size=22, color="black")


def generate_combined_report(energy_csv_path, trajectories_dir, output_html):
    # ==========================================
    # 2. PREPARE 1x3 SUBPLOTS
    # ==========================================
    fig = make_subplots(
        rows=1, cols=3,
        column_widths=[0.33, 0.33, 0.34],
        subplot_titles=(
            "<b>Individual Trial Trajectories</b>",
            "<b>Total Enclosed Area (Raw Bounds)</b>",
            "<b>Average Energy by Category</b>"
        ),
        horizontal_spacing=0.06
    )

    # ==========================================
    # 3. PROCESS TRAJECTORIES (LEFT & MIDDLE SUBPLOTS)
    # ==========================================
    window_size = 5
    smoothing_sigma = 10  # Only used for the solid Mean line
    scale_x = 18.2
    scale_y = 15.4

    for cat in ordered_cats:
        folder_path = os.path.join(trajectories_dir, cat.capitalize())
        if not os.path.exists(folder_path):
            folder_path = os.path.join(trajectories_dir, cat.upper())

        csv_files = glob.glob(os.path.join(folder_path, "*_warped.csv"))

        if not csv_files:
            print(f"No trajectory files found for category: {cat}")
            continue

        processed_trials = []
        for file in csv_files:
            try:
                group = pd.read_csv(file, sep=';', decimal=',')
            except Exception as e:
                print(f"Error reading {file}: {e}")
                continue

            # Process coordinates
            group['X'] = group['Transformed_X'] / scale_x
            group['Y'] = group['Transformed_Y'] / scale_y

            group['X_smooth'] = group['X'].rolling(window=window_size, min_periods=1).mean()
            group['Y_smooth'] = group['Y'].rolling(window=window_size, min_periods=1).mean()

            start_x = group['X_smooth'].iloc[0]
            start_y = group['Y_smooth'].iloc[0]
            group['X_norm'] = abs(group['X_smooth'] - start_x)
            group['Y_norm'] = group['Y_smooth'] - start_y

            processed_trials.append(group)

            # --- SUBPLOT 1: RAW INDIVIDUAL CURVES ---
            fig.add_trace(go.Scatter(
                x=group['X_norm'], y=group['Y_norm'],
                mode='lines',
                name=f"Raw {cat}",
                line=dict(color=colors[cat]['rgba'], width=1.5),
                opacity=0.6,
                showlegend=False,
                hoverinfo='skip'
            ), row=1, col=1)

        if not processed_trials:
            continue

        df_all_trials = pd.concat(processed_trials)
        df_all_trials['X_Rounded'] = df_all_trials['X_norm'].round(2)

        # --- GET EXACT MIN AND MAX AT EVERY X ---
        spatial_bounds = df_all_trials.groupby('X_Rounded')['Y_norm'].agg(['min', 'max', 'mean']).reset_index()

        x_vals = spatial_bounds['X_Rounded'].values
        y_lower_exact = spatial_bounds['min'].values
        y_upper_exact = spatial_bounds['max'].values

        # We only smooth the mean so it remains a sleek line through the middle
        smooth_mean = gaussian_filter1d(spatial_bounds['mean'].values, sigma=smoothing_sigma)

        # --- SUBPLOT 2: AREA ENCLOSED BY CURVES ---
        # Create a single, closed polygon array by concatenating the upper bound forward, and lower bound backward
        x_envelope = np.concatenate([x_vals, x_vals[::-1]])
        y_envelope = np.concatenate([y_upper_exact, y_lower_exact[::-1]])

        # The colored Area Shape
        fig.add_trace(go.Scatter(
            x=x_envelope,
            y=y_envelope,
            mode='lines',
            fill='toself',
            fillcolor=colors[cat]['pale'],
            line=dict(color='rgba(255,255,255,0)', width=0),
            showlegend=False,
            hoverinfo='skip'
        ), row=1, col=2)

        # The thick center line
        fig.add_trace(go.Scatter(
            x=x_vals, y=smooth_mean, mode='lines', name=f"<b>{cat_labels[cat]}</b>",
            line=dict(color=colors[cat]['rgba'], width=5, shape='spline'),
            showlegend=True
        ), row=1, col=2)

    # ==========================================
    # 4. PROCESS ENERGY BARS (RIGHT SUBPLOT)
    # ==========================================
    df_energy = pd.read_csv(energy_csv_path)

    def get_category_from_name(filename):
        name = str(filename).lower()
        for c in ordered_cats:
            if c in name: return c
        return 'other'

    df_energy['category'] = df_energy['csv name'].apply(get_category_from_name)
    df_energy = df_energy[df_energy['category'] != 'other']

    summary = df_energy.groupby('category')['cumulative energy'].agg(['mean', 'std']).reset_index()
    summary['category'] = pd.Categorical(summary['category'], categories=ordered_cats, ordered=True)
    summary = summary.sort_values('category').dropna()

    max_val = summary['mean'].max() + summary['std'].max()
    track_height = max_val * 1.15

    # Trace 1: Ghost Track
    fig.add_trace(go.Bar(
        x=[cat_labels[c] for c in summary['category']],
        y=[track_height] * len(summary),
        name='Track',
        marker_color='#f8fafc',
        marker_line_color='#cbd5e1',
        marker_line_width=2,
        hoverinfo='skip',
        showlegend=False,
        offsetgroup=1
    ), row=1, col=3)

    # Trace 2: Drop Shadow Offset
    fig.add_trace(go.Bar(
        x=[cat_labels[c] for c in summary['category']],
        y=summary['mean'],
        name='Shadow',
        marker_color='rgba(0,0,0,0.1)',
        hoverinfo='skip',
        showlegend=False,
        offsetgroup=1,
        dx=0.05
    ), row=1, col=3)

    # Trace 3: Liquid Glass Foreground
    bar_colors = [colors[c]['rgba'] for c in summary['category']]
    fig.add_trace(go.Bar(
        x=[cat_labels[c] for c in summary['category']],
        y=summary['mean'],
        name='Average Energy',
        marker_color=bar_colors,
        marker_line=dict(color='white', width=4),
        error_y=dict(type='data', array=summary['std'], color='#000000', thickness=3, width=8),
        hovertemplate="<b>Category:</b> %{x}<br><b>Avg Energy:</b> %{y:.2f} J<extra></extra>",
        offsetgroup=1,
        showlegend=False
    ), row=1, col=3)

    # ==========================================
    # 5. GLOBAL FORMATTING & LAYOUT
    # ==========================================
    fig.update_layout(
        title=dict(
            text="<b>Mass-Shift Kinematic Performance Analysis</b>",
            font=dict(family="Arial Black", size=42, color="black"),
            x=0.5, y=0.96
        ),
        barmode='overlay',
        height=950,
        width=2600,
        plot_bgcolor='white',
        paper_bgcolor='white',
        legend=dict(
            font=font_legend, orientation="h", yanchor="bottom", y=-0.15,
            xanchor="center", x=0.5, bgcolor="white",
            bordercolor="black", borderwidth=4,
            itemsizing="constant", itemwidth=60, traceorder="normal"
        ),
        margin=dict(l=80, r=80, t=150, b=150)
    )

    for annotation in fig['layout']['annotations']:
        annotation['font'] = font_title

    # --- AXIS FORMATTING ---
    fig.update_xaxes(title=dict(text="<b>Horizontal Distance (cm)</b>", font=font_axis),
                     tickfont=font_tick, gridcolor='black', gridwidth=1,
                     showline=True, linecolor='black', linewidth=3,
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=1)
    fig.update_yaxes(title=dict(text="<b>Lateral Drift (cm)</b>", font=font_axis),
                     tickfont=font_tick, gridcolor='black', gridwidth=1, scaleanchor="x", scaleratio=1,
                     showline=True, linecolor='black', linewidth=3,
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=1)

    fig.update_xaxes(title=dict(text="<b>Horizontal Distance (cm)</b>", font=font_axis),
                     tickfont=font_tick, gridcolor='black', gridwidth=1,
                     showline=True, linecolor='black', linewidth=3,
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=2)
    fig.update_yaxes(tickfont=font_tick, gridcolor='black', gridwidth=1, scaleanchor="x", scaleratio=1,
                     showline=True, linecolor='black', linewidth=3,
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=2)

    fig.update_xaxes(tickfont=font_tick, showgrid=False,
                     showline=True, linecolor='black', linewidth=3, row=1, col=3)
    fig.update_yaxes(title=dict(text="<b>Energy (J)</b>", font=font_axis),
                     tickfont=font_tick, showgrid=False,
                     showline=True, linecolor='black', linewidth=3,
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=3)

    fig.write_html(output_html)
    print(f"SUCCESS: Exported dashboard to {output_html}")


if __name__ == "__main__":
    trajectory_folder_path = r"D:\PREMALab\Mass-Shift\Code\Python\MultiTerr\Vids\Trajectories"
    energy_summary_file = 'D:\PREMALab\Mass-Shift\Code\Python\MultiTerr\energy_summary.csv'
    output_filename = "external_presentation_plots.html"

    generate_combined_report(energy_summary_file, trajectory_folder_path, output_filename)