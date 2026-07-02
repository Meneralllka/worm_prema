import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from scipy.stats import linregress
from scipy.ndimage import gaussian_filter1d
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. SETUP & AESTHETICS (Liquid Glass Theme)
# ==========================================
# High-contrast, vibrant "liquid" colors
colors = [
    {'name': 'Head Heavy', 'hex': '#f72585', 'rgba': 'rgba(247, 37, 133, 1)', 'pale': 'rgba(247, 37, 133, 0.25)'},
    {'name': 'Balanced', 'hex': '#4cc9f0', 'rgba': 'rgba(76, 201, 240, 1)', 'pale': 'rgba(76, 201, 240, 0.25)'},
    {'name': 'Tail Heavy', 'hex': '#84cc16', 'rgba': 'rgba(132, 204, 22, 1)', 'pale': 'rgba(132, 204, 22, 0.25)'}
]

# Big, bold Arial fonts - STRICTLY BLACK
font_title = dict(family="Arial Black, Arial, sans-serif", size=32, color="black")
font_axis = dict(family="Arial, sans-serif", size=24, color="black")
font_tick = dict(family="Arial, sans-serif", size=18, color="black")
font_legend = dict(family="Arial, sans-serif", size=26, color="black")

def create_external_figure():
    datasets = [
        {"file": r"D:\PREMALab\Mass-Shift\Code\Python\WaterVids\Head\all_combined_data_warped.csv", "label": "Head Heavy",
         "power": 15.5489},
        {"file": r"D:\PREMALab\Mass-Shift\Code\Python\WaterVids\Mid\all_combined_data_warped.csv", "label": "Balanced",
         "power": 14.7613},
        {"file": r"D:\PREMALab\Mass-Shift\Code\Python\WaterVids\Tail\all_combined_data_warped.csv", "label": "Tail Heavy",
         "power": 12.8666}
    ]

    mass_kg = 1.204
    g = 9.81
    window_size = 15
    smoothing_sigma = 30  # Controls how "melted/smooth" the polygon becomes

    # Conversion factors (Pixels to cm)
    scale_x = 18.2
    scale_y = 15.4

    # Data structures for the Bar Chart
    bar_data = {
        'labels': [],
        'x_vels_m': [], 'x_vels_s': [],
        'cot_recips_m': [], 'cot_recips_s': [],
        'h_mean_m': [], 'h_mean_s': []
    }

    # Setup 1x2 Subplot Grid
    fig = make_subplots(
        rows=1, cols=2,
        column_widths=[0.55, 0.45],
        subplot_titles=("<b>Trajectory Stability Array</b>", "<b>Kinematic Efficiency Profile</b>"),
        horizontal_spacing=0.08
    )

    # ==========================================
    # 2. PROCESS DATA
    # ==========================================
    for i, data_info in enumerate(datasets):
        try:
            df_full = pd.read_csv(data_info["file"], sep=';', decimal=',')
        except FileNotFoundError:
            print(f"Warning: Could not find {data_info['file']}. Skipping.")
            continue

        df_raw = df_full[df_full['Source_File'] != 'AVERAGE_PATH'].copy()

        processed_trials = []
        trial_metrics = {'x_vel': [], 'cot_recip': [], 'h_mean': []}

        # --- Process individual trials ---
        for source_file, group in df_raw.groupby('Source_File'):
            group = group.sort_values('Time').copy()

            # SCALE DATA TO CM
            # Note: If you meant multiply instead of divide, change the / to * below
            group['X'] = group['X'] / scale_x
            group['Y'] = group['Y'] / scale_y

            group['X_smooth'] = group['X'].rolling(window=window_size, min_periods=1).mean()
            group['Y_smooth'] = group['Y'].rolling(window=window_size, min_periods=1).mean()

            # Normalizing starting positions to (0,0) in cm
            start_x = group['X_smooth'].iloc[0]
            start_y = group['Y_smooth'].iloc[0]
            group['X_norm'] = abs(group['X_smooth'] - start_x)
            group['Y_norm'] = group['Y_smooth'] - start_y

            processed_trials.append(group)

            # Scalar Metrics (Time Window: 5s to 15s)
            group_filtered = group[(group['Time'] >= 5) & (group['Time'] <= 15)].copy()
            if len(group_filtered) < 2: continue

            # Regressions (abs_slope_x is now in cm/s)
            slope_x, _, _, _, _ = linregress(group_filtered['Time'], group_filtered['X_smooth'])
            abs_slope_x = abs(slope_x)

            # Cost of Transport
            # Note: For true dimensionless CoT, velocity should technically be in m/s.
            # If needed, you can convert it using: (abs_slope_x / 100)
            cot = data_info['power'] / (mass_kg * g * abs_slope_x) if abs_slope_x != 0 else np.nan
            cot_recip = 1.0 / cot if pd.notnull(cot) and cot != 0 else np.nan

            # Harmonic Mean (Vx & 1/CoT)
            if pd.notnull(cot_recip) and abs_slope_x > 0 and cot_recip > 0:
                h_mean_combined = 2 * (abs_slope_x * cot_recip) / (abs_slope_x + cot_recip)
            else:
                h_mean_combined = np.nan

            trial_metrics['x_vel'].append(abs_slope_x)
            trial_metrics['cot_recip'].append(cot_recip)
            trial_metrics['h_mean'].append(h_mean_combined)

        # Append aggregated means and std devs for the Bar Chart
        bar_data['labels'].append(data_info['label'])
        bar_data['x_vels_m'].append(np.nanmean(trial_metrics['x_vel']))
        bar_data['x_vels_s'].append(np.nanstd(trial_metrics['x_vel']))
        bar_data['cot_recips_m'].append(np.nanmean(trial_metrics['cot_recip']))
        bar_data['cot_recips_s'].append(np.nanstd(trial_metrics['cot_recip']))
        bar_data['h_mean_m'].append(np.nanmean(trial_metrics['h_mean']))
        bar_data['h_mean_s'].append(np.nanstd(trial_metrics['h_mean']))

        # --- Aggregate Trajectory by Distance (X) for Subplot 1 ---
        df_all_trials = pd.concat(processed_trials)
        # Because we are now in cm, round to 1 decimal place (millimeters) to keep data fidelity
        df_all_trials['X_Rounded'] = df_all_trials['X_norm'].round(1)
        spatial_avg = df_all_trials.groupby('X_Rounded')['Y_norm'].agg(['mean', 'std']).reset_index()
        spatial_avg.dropna(subset=['std'], inplace=True)

        # 1D Gaussian Filtering to create the sleek "Liquid Polygon" look
        x_vals = spatial_avg['X_Rounded'].values
        smooth_mean = gaussian_filter1d(spatial_avg['mean'].values, sigma=smoothing_sigma)
        smooth_std = gaussian_filter1d(spatial_avg['std'].values, sigma=smoothing_sigma)

        y_upper = smooth_mean + smooth_std
        y_lower = smooth_mean - smooth_std

        # ==========================================
        # PLOT 1: Liquid Trajectory Map
        # ==========================================
        # Invisible Lower Bound
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_lower, mode='lines',
            line=dict(width=0), showlegend=False, hoverinfo='skip'
        ), row=1, col=1)

        # Sweeping Polygon Area (Standard Deviation bounds)
        fig.add_trace(go.Scatter(
            x=x_vals, y=y_upper, mode='lines', fill='tonexty',
            fillcolor=colors[i]['pale'], line=dict(width=0),
            showlegend=False, hoverinfo='skip'
        ), row=1, col=1)

        # Sweeping Solid Mean Path
        fig.add_trace(go.Scatter(
            x=x_vals, y=smooth_mean, mode='lines', name=f"<b>{data_info['label']}</b>",
            line=dict(color=colors[i]['rgba'], width=7, shape='spline'),
            showlegend=True
        ), row=1, col=1)

    # ==========================================
    # PLOT 2: Linear Kinematic Metrics (Bars)
    # ==========================================
    metric_labels = ['<b>Forward Speed</b><br>(Vx)', '<b>Efficiency</b><br>(1/CoT)',
                     '<b>Harmonic Score</b><br>(Composite)']

    # Error bars explicitly forced to black
    error_style = dict(type='data', color='black', thickness=3, width=8)

    for i in range(len(datasets)):
        y_means = [bar_data['x_vels_m'][i], bar_data['cot_recips_m'][i], bar_data['h_mean_m'][i]]
        y_errs = [bar_data['x_vels_s'][i], bar_data['cot_recips_s'][i], bar_data['h_mean_s'][i]]

        fig.add_trace(go.Bar(
            name=bar_data['labels'][i],
            x=metric_labels,
            y=y_means,
            marker_color=colors[i]['rgba'],
            offsetgroup=i,
            error_y=dict(**error_style, array=y_errs),
            showlegend=False
        ), row=1, col=2)

    # ==========================================
    # 3. GLOBAL LIQUID AESTHETICS & LAYOUT
    # ==========================================
    fig.update_layout(
        title=dict(text="<b>Mass-Shift Kinematic Performance Analysis</b>",
                   font=dict(family="Arial Black", size=42, color="black"), x=0.5, y=0.95),
        height=1000, width=2200,
        plot_bgcolor='white',
        paper_bgcolor='white',
        barmode='group',
        legend=dict(
            font=font_legend, orientation="h", yanchor="bottom", y=-0.15,
            xanchor="center", x=0.5, bgcolor="white",
            bordercolor="black", borderwidth=2,  # Black Legend Frame
            itemsizing="constant", itemwidth=60, traceorder="normal"
        ),
        margin=dict(l=100, r=80, t=180, b=180)
    )

    # Update Subplot Titles Font (Black)
    for annotation in fig['layout']['annotations']:
        annotation['font'] = font_title

    # Axis Styling Subplot 1 (Trajectory Map) - Sharp Black Lines
    fig.update_xaxes(title=dict(text="<b>Horizontal Distance (cm)</b>", font=font_axis), tickfont=font_tick,
                     gridcolor='black', gridwidth=1,
                     showline=True, linecolor='black', linewidth=3,  # Outer Box frame
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=1)

    # Added scaleanchor and scaleratio to force 1:1 true scale
    fig.update_yaxes(title=dict(text="<b>Lateral Drift (cm)</b>", font=font_axis), tickfont=font_tick,
                     gridcolor='black', gridwidth=1,
                     scaleanchor="x", scaleratio=1,  # <--- THIS FORCES EQUAL SCALING
                     showline=True, linecolor='black', linewidth=3,  # Outer Box frame
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=1)

    # Axis Styling Subplot 2 (Bars) - NO GRID, Sharp Black Lines
    fig.update_xaxes(tickfont=font_tick,
                     showgrid=False,  # Grid disabled
                     showline=True, linecolor='black', linewidth=3,  # Outer Box frame
                     row=1, col=2)

    fig.update_yaxes(title=dict(text="<b>Kinematic Value</b>", font=font_axis), tickfont=font_tick,
                     showgrid=False,  # Grid disabled
                     showline=True, linecolor='black', linewidth=3,  # Outer Box frame
                     zeroline=True, zerolinecolor='black', zerolinewidth=2, row=1, col=2)

    # Output exports
    fig.write_html("external_presentation_plots.html")

    try:
        fig.write_image("external_presentation_plots.svg")
        fig.write_image("external_presentation_plots.png", scale=3)
        print("SUCCESS: Exported 'external_presentation_plots' as HTML, SVG, and high-res PNG.")
    except Exception as e:
        print("SUCCESS: Exported 'external_presentation_plots.html'. (Install 'kaleido' for image export).")

if __name__ == "__main__":
    create_external_figure()