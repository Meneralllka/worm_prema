import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import os

# --- 1. Load and Clean the Data ---
path_exp = r'F:\PREMALab\Mass-Shift\Experiments\Data\RawExp.csv'
output_dir = r'F:\PREMALab\Mass-Shift\Experiments\Figures'

# Create the directory if it doesn't exist
if not os.path.exists(output_dir):
    os.makedirs(output_dir)


def load_clean_data(filepath):
    df = pd.read_csv(filepath)
    cols_to_fix = ['Lag', 'Vel (cm/s)', 'Amplitude']
    for col in cols_to_fix:
        if col in df.columns:
            if df[col].dtype == object:
                df[col] = df[col].str.replace(',', '.')
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df.dropna(subset=['Lag', 'Amplitude', 'Vel (cm/s)'])


df_exp = load_clean_data(path_exp)
water_placements = df_exp['Water (H, T)'].unique()

# --- Font Size Configuration ---
TITLE_SIZE = 40
SUBPLOT_TITLE_SIZE = 32
AXIS_LABEL_SIZE = 32
TICK_LABEL_SIZE = 32
COLORBAR_TITLE_SIZE = 32
COLORBAR_TICK_SIZE = 32

# ==========================================
# --- 2. GENERATE 1x3 2D HEATMAPS (EXP) ---
# ==========================================
titles = [f"Exp Water: {wp}" for wp in water_placements]

fig_2d = make_subplots(
    rows=1, cols=len(water_placements),
    subplot_titles=titles,
    horizontal_spacing=0.08
)

for i, wp in enumerate(water_placements):
    sub_exp = df_exp[df_exp['Water (H, T)'] == wp].sort_values(by=['Lag', 'Amplitude'])

    Z_pivot = sub_exp.pivot_table(
        index='Lag',
        columns='Amplitude',
        values='Vel (cm/s)',
        aggfunc='mean'
    )

    fig_2d.add_trace(
        go.Contour(
            x=Z_pivot.columns,
            y=Z_pivot.index,
            z=Z_pivot.values,
            colorscale='Plasma',
            connectgaps=True,
            line_smoothing=0.85,
            showscale=(i == len(water_placements) - 1),
            colorbar=dict(
                title=dict(text="Vel (cm/s)", font=dict(size=COLORBAR_TITLE_SIZE)),
                tickfont=dict(size=COLORBAR_TICK_SIZE),
                thickness=30,
                len=0.8,
                yanchor='middle',
                y=0.5
            )
        ),
        row=1, col=i + 1
    )

    fig_2d.add_trace(
        go.Scatter(
            x=sub_exp['Amplitude'],
            y=sub_exp['Lag'],
            mode='markers',
            marker=dict(color='white', size=6, opacity=0.4, line=dict(width=1, color='black')),
            showlegend=False
        ),
        row=1, col=i + 1
    )

    fig_2d.update_xaxes(title_text="Amplitude", title_font=dict(size=AXIS_LABEL_SIZE),
                        tickfont=dict(size=TICK_LABEL_SIZE), row=1, col=i + 1)
    fig_2d.update_yaxes(title_text="Lag", title_font=dict(size=AXIS_LABEL_SIZE),
                        tickfont=dict(size=TICK_LABEL_SIZE), row=1, col=i + 1)

for annotation in fig_2d['layout']['annotations']:
    annotation['font'] = dict(size=SUBPLOT_TITLE_SIZE)

fig_2d.update_layout(
    title=dict(text='Experimental Robot Performance Analysis', font=dict(size=TITLE_SIZE), x=0.5, y=0.95),
    height=700, width=1800, margin=dict(l=100, r=100, b=120, t=180), plot_bgcolor='white'
)

# --- SAVE SECTION ---
html_path = os.path.join(output_dir, 'Robot_Experimental_Only.html')
png_path = os.path.join(output_dir, 'Robot_Experimental_Only.png')

fig_2d.write_html(html_path)
print(f"Saved HTML to: {html_path}")

try:
    # Scale=2 makes it high resolution
    fig_2d.write_image(png_path, engine="kaleido", scale=2)
    print(f"Saved PNG to: {png_path}")
except Exception as e:
    print(f"PNG export failed. Error: {e}")
    print("Ensure you have kaleido installed: pip install kaleido")
