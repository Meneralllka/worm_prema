'''import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import plotly.colors as pcolors
import warnings

# Suppress warnings
warnings.filterwarnings('ignore')

# ==========================================
# 1. READ AND PREPROCESS DATA
# ==========================================
try:
    df = pd.read_csv("FinalExp_Ground - Лист1.csv")
except FileNotFoundError:
    raise FileNotFoundError("Csv file not found. Please provide the correct file path.")

cols_to_convert = ['Vel (cm/s)', 'CoT', 'Lag']
for col in cols_to_convert:
    if col in df.columns and df[col].dtype == object:
        df[col] = df[col].astype(str).str.replace(',', '.')

df['Vel_num'] = pd.to_numeric(df['Vel (cm/s)'], errors='coerce')
df['CoT_num'] = pd.to_numeric(df['CoT'], errors='coerce').abs()

df['is_unst_vel'] = df['Vel (cm/s)'].astype(str).str.lower().str.contains('unst') | df['Vel_num'].isna()
df['is_unst_cot'] = df['CoT'].astype(str).str.lower().str.contains('unst') | df['CoT_num'].isna()
df['is_outlier_cot'] = df['CoT_num'].abs() > 100
df['is_neg_vel'] = df['Vel_num'] < 0

df.loc[df['is_unst_vel'], 'Vel_num'] = np.nan
df.loc[df['is_unst_cot'] | df['is_outlier_cot'], 'CoT_num'] = np.nan

def calc_hm(row):
    v_raw = row['Vel_num']
    v_mag = abs(v_raw) if pd.notna(v_raw) else np.nan
    c = row['CoT_num'] if pd.notna(row['CoT_num']) else np.nan

    if pd.isna(v_mag) or pd.isna(c) or v_mag == 0 or c == 0:
        return np.nan

    inv_c = 1.0 / c
    hm_mag = 2 * v_mag * inv_c / (v_mag + inv_c)

    return hm_mag if v_raw >= 0 else -hm_mag

df['HM_num'] = df.apply(calc_hm, axis=1)

df['Amplitude'] = df['Amplitude'].astype(str)
df['Lag'] = df['Lag'].astype(str)
df['Water (H, T)'] = df['Water (H, T)'].astype(str)

waters = ['(100, 0)', '(50, 50)', '(0, 100)']

# ==========================================
# 2. PUBLICATION DESIGN STANDARDS
# ==========================================
axis_font = dict(family="Arial, sans-serif", size=48, color="#000000")
tick_font = dict(family="Arial, sans-serif", size=36, color="#000000")
legend_font = dict(family="Arial, sans-serif", size=42, color="#000000")

publication_layout = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=axis_font,
    margin=dict(l=120, r=600, t=100, b=120),

    # MAIN LEGEND (For Lags)
    legend=dict(
        bgcolor='rgba(255,255,255,0.95)',
        bordercolor='black',
        borderwidth=2.5,
        font=legend_font,
        title=dict(text="Lag", font=dict(family="Arial, sans-serif", size=48, color="black")),
        orientation="v",
        yanchor="top",
        y=1.0,
        xanchor="left",
        x=0.81,
        itemsizing='constant',
        itemwidth=100,
        tracegroupgap=15
    ),

    # MOTOR LEGEND (For Subplot D)
    legend2=dict(
        bgcolor='rgba(255,255,255,0.95)',
        bordercolor='black',
        borderwidth=2.5,
        font=legend_font,
        title=dict(text="Motors", font=dict(family="Arial, sans-serif", size=48, color="black")),
        orientation="v",
        yanchor="top",
        y=1.0,
        xanchor="left",
        x=0.93,
        itemsizing='constant',
        itemwidth=100
    )
)

common_xaxis = dict(
    showline=True, linewidth=2.5, linecolor='black', mirror=True,
    ticks='outside', tickwidth=2, ticklen=6, tickcolor='black',
    gridcolor='#E5E5E5', gridwidth=1, showgrid=True, zeroline=False,
    tickfont=tick_font, title_font=axis_font
)

common_yaxis = dict(
    showline=True, linewidth=2.5, linecolor='black', mirror=True,
    ticks='outside', tickwidth=2, ticklen=6, tickcolor='black',
    gridcolor='#E5E5E5', gridwidth=1, showgrid=True, zeroline=False,
    tickfont=tick_font, title_font=axis_font
)


def with_alpha(color, alpha):
    """Return a Plotly-friendly rgba color with the requested alpha."""
    color = str(color).strip()

    if color.startswith("rgba") or color.startswith("rgb"):
        inside = color[color.find("(") + 1:color.rfind(")")]
        parts = [part.strip() for part in inside.split(",")]
        if len(parts) >= 3:
            return f"rgba({parts[0]}, {parts[1]}, {parts[2]}, {alpha})"

    if color.startswith("#"):
        hex_color = color.lstrip("#")
        if len(hex_color) == 3:
            hex_color = "".join(ch * 2 for ch in hex_color)
        if len(hex_color) == 6:
            r, g, b = (int(hex_color[i:i + 2], 16) for i in (0, 2, 4))
            return f"rgba({r}, {g}, {b}, {alpha})"

    return color

# ==========================================
# 3. COMBINED MASTER PLOT CREATION
# ==========================================
def create_master_plot(file_prefix):
    df_70 = df[df['Amplitude'] == '70'].copy()

    try:
        lags = sorted(df_70['Lag'].unique(), key=lambda x: float(x))
    except ValueError:
        lags = sorted(df_70['Lag'].unique())

    safe_spectral = [
        [0.0, '#9E0142'],
        [0.2, '#D53E4F'],
        [0.4, '#F46D43'],
        [0.6, '#66C2A5'],
        [0.8, '#3288BD'],
        [1.0, '#5E4FA2']
    ]
    colors = pcolors.sample_colorscale(safe_spectral, np.linspace(0, 1, len(lags)))

    sim_data = {
        '0.2': [19.8, 10.5, 3.7],
        '1.2': [7.6, 4.5, 1.4],
        '2.2': [4.1, 2.4, 0.6]
    }

    fig = make_subplots(rows=1, cols=4, horizontal_spacing=0.08)

    metrics = [
        ('Vel_num', 'Velocity (cm/s)'),
        ('CoT_num', 'Cost of Transport'),
        ('HM_num', 'Harmonic Mean')
    ]

    lag_trace_data = []

    for lag_idx, lag in enumerate(lags):
        df_lag = df_70[df_70['Lag'] == lag]
        color = colors[lag_idx]

        try:
            lag_key = str(float(lag))
            is_redflag = (float(lag) == 0.2)
        except ValueError:
            lag_key = str(lag).strip()
            is_redflag = (str(lag).strip() == '0.2')

        marker_symbol = 'triangle-down' if is_redflag else 'circle'
        legend_name = f'{lag} (Unstable)' if is_redflag else f'{lag}'

        lag_trace_data.append({
            'lag_key': lag_key,
            'color': color,
            'marker_symbol': marker_symbol,
            'legend_name': legend_name,
            'df_lag': df_lag,
        })

    # Draw all simulation traces first so the real data can sit on top.
    for trace_info in lag_trace_data:
        lag_key = trace_info['lag_key']
        color = trace_info['color']
        if lag_key not in sim_data:
            continue

        sim_color = with_alpha(color, 0.98)
        fig.add_trace(go.Scatter(
            x=waters,
            y=sim_data[lag_key],
            mode='lines+markers',
            name=f'{lag_key} (Sim)',
            legendgroup=lag_key,
            line=dict(color=sim_color, width=4, dash='dash'),
            marker=dict(symbol='square', color=sim_color, size=45, line=dict(color='black', width=2)),
            opacity=0.8,
            showlegend=True,
            legend="legend"
        ), row=1, col=1)

    # Draw all experimental traces second so they overlay the simulation traces.
    for trace_info in lag_trace_data:
        lag_key = trace_info['lag_key']
        color = trace_info['color']
        marker_symbol = trace_info['marker_symbol']
        legend_name = trace_info['legend_name']
        df_lag = trace_info['df_lag']

        for col_idx, (metric_col, ylabel) in enumerate(metrics, start=1):
            y_values = []
            for w in waters:
                subset = df_lag[df_lag['Water (H, T)'] == w]
                if not subset.empty:
                    y_values.append(subset[metric_col].iloc[0])
                else:
                    y_values.append(np.nan)

            exp_color = with_alpha(color, 0.98)
            fig.add_trace(go.Scatter(
                x=waters,
                y=y_values,
                mode='lines+markers',
                name=f"{legend_name} (Exp)",
                legendgroup=lag_key,
                line=dict(color=exp_color, width=4, dash='solid'),
                marker=dict(symbol=marker_symbol, color=exp_color, size=60, line=dict(color='black', width=2)),
                opacity=0.8,
                showlegend=(col_idx == 1),
                legend="legend"
            ), row=1, col=col_idx)

    # Highlight Best Overall Option in C
    df_valid = df_70[~df_70['Lag'].astype(str).str.strip().isin(['0.2', '0.20'])]
    if not df_valid.empty and not df_valid['HM_num'].isna().all():
        best_idx = df_valid['HM_num'].idxmax()
        best_row = df_valid.loc[best_idx]
        fig.add_annotation(
            x=best_row['Water (H, T)'], y=best_row['HM_num'],
            xref="x3", yref="y3", text=f"⭐ <b>Best Overall</b><br>(Lag {best_row['Lag']})",
            showarrow=True, arrowhead=2, arrowsize=1.5, arrowwidth=4, arrowcolor="#E6A100",
            ax=0, ay=-90, font=dict(family="Arial, sans-serif", size=31, color="#000000"),
            bgcolor="rgba(255, 255, 255, 0.95)", bordercolor="#E6A100", borderwidth=3, borderpad=6
        )

    for i in range(1, 4):
        metric_name = metrics[i-1][0]
        max_y = df_70[metric_name].max()
        min_y = df_70[metric_name].min()

        if pd.isna(max_y) or pd.isna(min_y):
            lower_bound, upper_bound = 0, 100
        else:
            y_range = max_y - min_y
            if y_range == 0: y_range = abs(max_y) * 0.5 if max_y != 0 else 10
            upper_bound = max_y + (y_range * 0.40)
            lower_bound = min_y - (y_range * 0.15)

        fig.update_xaxes(
            title_text="Water Percentage (Head, Tail)",
            categoryorder='array', categoryarray=waters,
            **common_xaxis, row=1, col=i
        )
        fig.update_yaxes(
            title_text=metrics[i-1][1], range=[lower_bound, upper_bound],
            **common_yaxis, row=1, col=i
        )
        if i in [1, 3]:
            fig.update_yaxes(zeroline=True, zerolinewidth=2, zerolinecolor='rgba(0,0,0,0.3)', row=1, col=i)

    # ---------------------------------------------------------
    # SUBPLOT D (CONCEPT OF LAG AND AMPLITUDE)
    # ---------------------------------------------------------
    t = np.linspace(0, 2 * np.pi, 500)
    demo_amp = 70
    demo_lag = 1.2
    joint_colors = pcolors.sample_colorscale(safe_spectral, np.linspace(0, 1, 4))

    for j in range(4):
        wave_y = np.maximum(0, demo_amp * np.sin(t - j * demo_lag))

        fig.add_trace(go.Scatter(
            x=t, y=wave_y, mode='lines',
            name=f'Motor {j+1}',
            line=dict(color=joint_colors[j], width=12),
            showlegend=True,
            legend="legend2"
        ), row=1, col=4)

    fig.update_xaxes(
        title=dict(text="Phase / Time", font=axis_font, standoff=40),
        range=[0, 2 * np.pi], row=1, col=4,
        tickvals=[0, np.pi/2, np.pi, 3*np.pi/2, 2*np.pi],
        ticktext=["0", "π/2", "π", "3π/2", "2π"],
        **common_xaxis
    )

    fig.update_yaxes(
        title=dict(text="Joint Angle (°)", font=axis_font, standoff=40),
        range=[-10, 130], domain=[0.0, 0.48], row=1, col=4,
        **common_yaxis
    )
    fig.update_yaxes(zeroline=True, zerolinewidth=3, zerolinecolor='black', row=1, col=4)

    letters = ['A', 'B', 'C', 'D']
    for i in range(1, 5):
        axis_suffix = str(i) if i > 1 else ""
        fig.add_annotation(
            x=0.01, y=0.99, xref=f"x{axis_suffix} domain", yref=f"y{axis_suffix} domain",
            text=f"<b>{letters[i-1]}</b>", showarrow=False,
            font=dict(family="Arial, sans-serif", size=46, color="#000000"),
            bgcolor="white", bordercolor="black", borderwidth=2.5, borderpad=10,
            xanchor="left", yanchor="top"
        )

    fig.update_layout(
        width=4200, height=1100,
        **publication_layout
    )

    fig.write_html(f'{file_prefix}_master_plot.html')
    try:
        fig.write_image(f'{file_prefix}_master_plot.svg')
    except Exception as e:
        pass

create_master_plot('amp70')
'''

import plotly.graph_objects as go

# Extracted Data
# Ordered from bottom to top to match the image's layout
y_labels = ['(100, 0)', '(50, 50)', '(0, 100)']
x_values = [3.24, 3.09, 2.94]
text_labels = ['3.24 N', '3.09 N', '2.94 N']

# Create the figure
fig = go.Figure(go.Bar(
    x=x_values,
    y=y_labels,
    orientation='h',
    text=text_labels,
    textposition='outside',
    textfont=dict(family="Arial", size=18, color="black"),
    marker=dict(color='#F09898') # Pink color matching the image
))

# Update layout to match styling, fonts, and axes limits
fig.update_layout(
    font=dict(family="Arial", size=16, color="black"),
    xaxis=dict(
        title=dict(
            text="<b>Traction Force (N)</b>",
            font=dict(family="Arial", size=22, color="black")
        ),
        tickvals=[2.5, 3.0, 3.5],
        range=[2.5, 3.6], # Clipped at 2.5 to match image, 3.6 gives room for annotations
        showgrid=True,
        gridcolor='#E5E5E5',
        showline=True,
        linewidth=1,
        linecolor='black',
        zeroline=False
    ),
    yaxis=dict(
        title=dict(
            text="<b>Water Distribution<br>(Head, Tail) (%)</b>",
            font=dict(family="Arial", size=22, color="black")
        ),
        showgrid=False,
        showline=True,
        linewidth=1,
        linecolor='black',
    ),
    plot_bgcolor='white',
    margin=dict(l=150, r=20, t=40, b=60), # Adjust margins to prevent label clipping
    bargap=0.3 # Adjust spacing between the horizontal bars
)

# Output generation
# 1. Save as interactive HTML
fig.write_html("traction_force_barchart.html")

# 2. Save as scalable vector graphic (SVG)
# Note: Ensure you have the 'kaleido' package installed to write image files
fig.write_image("traction_force_barchart.svg")

# Display the figure in your IDE or notebook
fig.show()