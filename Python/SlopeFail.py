"""import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. READ AND PREPROCESS DATA
# ==========================================
df = pd.read_csv("FinalExp_Ground_Slope - Лист1.csv")

df['Slope Angle'] = df['Slope Angle'].str.replace(',', '.').astype(float)
df['Lag'] = df['Lag'].str.replace(',', '.').astype(float)

status_map = {'100': 3, '50': 2, 'S': 1, 'F': 0}
df['Color_Val'] = df['Stable?'].map(status_map)

# Liquid Glass Modern Palette
outcome_labels = {3: 'Success (100)', 2: 'Success (50)', 1: 'Steady', 0: 'Fail'}
outcome_colors = {
    3: '#059669',  # Emerald Green
    2: '#34d399',  # Soft Mint
    1: '#f59e0b',  # Vibrant Amber
    0: '#ef4444'  # Vibrant Crimson
}

# ==========================================
# 2. SETUP GRID
# ==========================================
waters = ['(100, 0)', '(50, 50)', '(0, 100)']
water_names = ['Head Heavy', 'Balanced', 'Tail Heavy']
lags = [0.4, 0.8, 1.2]

# 2 Rows: 10.0 and 19.5 degrees
slopes = [10.0, 19.5]

# Y-Axis Mapping (2 rows)
y_vals_map = {10.0: 0, 19.5: 1}
y_labels = ["10.0°", "19.5°"]

# X-Axis Labels
x_labels = [f"{l}s" for l in lags] * 3

# Grid dimensions (2, 9)
z_grid = np.zeros((2, 9))
text_grid = np.empty((2, 9), dtype=object)

for s in slopes:
    r_idx = y_vals_map[s]
    c_idx = 0
    for w in waters:
        for l in lags:
            match = df[(df['Slope Angle'] == s) & (df['Water (H, T)'] == w) & (df['Lag'] == l)]
            if not match.empty:
                val = match['Color_Val'].values[0]
                z_grid[r_idx, c_idx] = val
                text_grid[r_idx, c_idx] = f"Outcome: {outcome_labels[val]}<br>Water: {w}<br>Lag: {l}s<br>Slope: {s}°"
            else:
                z_grid[r_idx, c_idx] = np.nan
            c_idx += 1

# ==========================================
# 3. DESIGN & SHAPES
# ==========================================
axis_font = dict(family="Arial, sans-serif", size=60, color="#1e293b")
tick_font = dict(family="Arial, sans-serif", size=48, color="#334155")
legend_font = dict(family="Arial, sans-serif", size=60, color="#1e293b")

bg_colors = [
    'rgba(56, 189, 248, 0.65)',  # Bright Sky Blue
    'rgba(148, 163, 184, 0.65)',  # Bright Amethyst Purple
    'rgba(251, 146, 60, 0.65)'  # Bright Orange/Coral
]


def get_shadow_path(x, y, size=0.82, r=0.2, off_x=0.04, off_y=-0.04):
    x0, x1 = x - size / 2 + off_x, x + size / 2 + off_x
    y0, y1 = y - size / 2 + off_y, y + size / 2 + off_y
    return f"M {x0 + r},{y0} L {x1 - r},{y0} Q {x1},{y0} {x1},{y0 + r} L {x1},{y1 - r} Q {x1},{y1} {x1 - r},{y1} L {x0 + r},{y1} Q {x0},{y1} {x0},{y1 - r} L {x0},{y0 + r} Q {x0},{y0} {x0 + r},{y0} Z"


def get_base_path(x, y, size=0.82, r=0.2):
    x0, x1 = x - size / 2, x + size / 2
    y0, y1 = y - size / 2, y + size / 2
    return f"M {x0 + r},{y0} L {x1 - r},{y0} Q {x1},{y0} {x1},{y0 + r} L {x1},{y1 - r} Q {x1},{y1} {x1 - r},{y1} L {x0 + r},{y1} Q {x0},{y1} {x0},{y1 - r} L {x0},{y0 + r} Q {x0},{y0} {x0 + r},{y0} Z"


# ==========================================
# 4. BUILD FIGURE
# ==========================================
fig = go.Figure()

# Background Zones
for i in range(3):
    fig.add_shape(
        type="rect",
        x0=i * 3 - 0.5, x1=i * 3 + 2.5,
        y0=-0.5, y1=1.5,
        fillcolor=bg_colors[i],
        line_width=0, layer="below"
    )

# Tiles
hover_x, hover_y, hover_text = [], [], []

for r in range(2):
    for c in range(9):
        val = z_grid[r, c]
        if not np.isnan(val):
            # 1. Drop Shadow
            fig.add_shape(type="path", path=get_shadow_path(c, r), fillcolor="rgba(0,0,0,0.15)", line_width=0,
                          layer="above")
            # 2. Base Colored Tile (With frosted white border)
            fig.add_shape(type="path", path=get_base_path(c, r), fillcolor=outcome_colors[int(val)],
                          line=dict(color='rgba(255,255,255,0.9)', width=4), layer="above")

            hover_x.append(c)
            hover_y.append(r)
            hover_text.append(text_grid[r, c])

# Tooltip scatter layer
fig.add_trace(go.Scatter(x=hover_x, y=hover_y, mode='markers', marker=dict(size=100, opacity=0), text=hover_text,
                         hoverinfo='text', showlegend=False))

# Legends setup
for val in [3, 2, 1, 0]:
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', name=outcome_labels[val], legend='legend',
                             marker=dict(size=60, color=outcome_colors[val], symbol='square',
                                         line=dict(color="rgba(255,255,255,0.9)", width=4))))

for name, color in zip(water_names, bg_colors):
    solid_color = color.replace('0.65)', '0.9)')
    fig.add_trace(go.Scatter(x=[None], y=[None], mode='markers', name=f"{name}", legend='legend2',
                             marker=dict(size=60, color=solid_color, symbol='square',
                                         line=dict(color="rgba(255,255,255,0.9)", width=4))))

# ==========================================
# 5. LAYOUT & ANNOTATIONS
# ==========================================
fig.update_layout(
    # UPDATED: Width is now 3000px.
    # With margins l=200, r=100 (Total 300), the plot width is exactly 2700px.
    # With height 1600px, margins t=300, b=700 (Total 1000), the plot height is exactly 600px.
    # 2700px / 600px = 4.5. Our data is 9 units wide / 2 units tall = 4.5. White space is eradicated.
    width=3000, height=1600,
    plot_bgcolor='white', paper_bgcolor='white',
    margin=dict(l=200, r=100, t=300, b=700),
    yaxis=dict(scaleanchor="x", scaleratio=1),

    legend=dict(
        title=dict(text="Outcome (Cell Color)", font=legend_font),
        font=legend_font, orientation="h", yanchor="top", y=-0.35, xanchor="center", x=0.5,
        bgcolor='white', bordercolor='#cbd5e1', borderwidth=4, itemwidth=120
    ),
    legend2=dict(
        title=dict(text="Water Placement (Background Zone)", font=legend_font),
        font=legend_font, orientation="h", yanchor="top", y=-0.55, xanchor="center", x=0.5,
        bgcolor='white', bordercolor='#cbd5e1', borderwidth=4, itemwidth=120
    )
)

# Clean Axes
fig.update_xaxes(
    title_text="Lag Time (s)", title_font=dict(family="Arial", size=70, color="black"), tickfont=tick_font,
    tickvals=list(range(9)), ticktext=x_labels,
    showline=True, linewidth=6, linecolor='#64748b', mirror=True, ticks='outside', ticklen=20, tickwidth=6,
    range=[-0.5, 8.5]
)

fig.update_yaxes(
    title_text="Slope Angle (°)", title_font=dict(family="Arial", size=70, color="black"), tickfont=tick_font,
    tickvals=[0, 1], ticktext=y_labels,
    showline=True, linewidth=6, linecolor='#64748b', mirror=True, ticks='outside', ticklen=20, tickwidth=6,
    range=[-0.5, 1.5]
)

# Sleek Header Annotations
annotations = []
for i, name in enumerate(water_names):
    annotations.append(dict(
        x=i * 3 + 1, y=1.65, xref="x", yref="y",
        text=f"<b>{name}</b>",
        showarrow=False,
        font=dict(family="Arial", size=70, color="black"),
        bgcolor="rgba(255,255,255,0.8)", bordercolor="black", borderwidth=4, borderpad=15
    ))
fig.update_layout(annotations=annotations)

try:
    fig.write_image('Final_LiquidGlass_Plotly.svg', format='svg')
    print("SVG successfully saved!")
except Exception as e:
    print(f"Error saving SVG: {e}")

# Output
fig.write_html('Final_LiquidGlass_Plotly.html')
fig.show()
"""
import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. READ AND PREPROCESS DATA
# ==========================================
df = pd.read_csv("FinalExp_Ground_Slope - Лист1.csv")

# Clean formatting
df['Slope Angle'] = df['Slope Angle'].astype(str).str.replace(',', '.').astype(float)
df['Lag'] = df['Lag'].astype(str).str.replace(',', '.').astype(float)


# Safely parse numerical values, treating 'S' and 'F' as 0.0
def parse_float(val, status):
    if status in ['S', 'F']: return 0.0
    try:
        return float(str(val).replace(',', '.'))
    except:
        return 0.0


df['Velocity'] = df.apply(lambda r: parse_float(r['Vel (cm/s)'], r['Stable?']), axis=1)
df['CoT'] = df.apply(lambda r: parse_float(r['CoT (P/mgV)'], r['Stable?']), axis=1)

# ==========================================
# 2. LIQUID GLASS DESIGN & SCALING SETUP
# ==========================================
lags = [0.4, 0.8, 1.2]
slopes = [10.0, 19.5]

waters = ['(100, 0)', '(50, 50)']
water_names = ['Head Heavy', 'Balanced']

# Colors represent Lag Time
color_map = {
    0.4: 'rgba(56, 189, 248, 0.95)',  # Sky Blue
    0.8: 'rgba(236, 72, 153, 0.95)',  # Magenta
    1.2: 'rgba(251, 146, 60, 0.95)'  # Vibrant Orange
}

# Line styles represent Water Distribution
dash_map = {
    '(100, 0)': 'solid',
    '(50, 50)': 'dash'
}

text_color = '#1e293b'
grid_color = '#cbd5e1'

# DYNAMIC PROPORTIONAL SCALING
plot_df = df[df['Slope Angle'].isin(slopes)]
valid_runs = plot_df[(plot_df['Velocity'] > 0) & (plot_df['CoT'] > 0)]

# 10% headroom to maximize canvas usage
v_max = valid_runs['Velocity'].max() * 1.10
c_max = valid_runs['CoT'].max() * 1.10

if pd.isna(v_max) or v_max == 0: v_max = 10.0  # Failsafe
if pd.isna(c_max) or c_max == 0: c_max = 10.0

# ==========================================
# 3. BUILD COMBINED SLOPEGRAPH
# ==========================================
fig = go.Figure()

# 1. GHOST TRACKS (Axis Pillars)
fig.add_shape(type="line", x0=0, x1=0, y0=-0.02, y1=1.02, line=dict(color=grid_color, width=8))
fig.add_shape(type="line", x0=1, x1=1, y0=-0.02, y1=1.02, line=dict(color=grid_color, width=8))

# 2. Axis Headers
fig.add_annotation(x=0, y=1.08, text=f"<b>Velocity</b><br>(Max: {v_max:.1f})", showarrow=False,
                   font=dict(size=32, color=text_color, family="Arial"))
fig.add_annotation(x=1, y=1.08, text=f"<b>CoT</b><br>(Max: {c_max:.1f})", showarrow=False,
                   font=dict(size=32, color=text_color, family="Arial"))

# 3. Plot Data Lines
for slope in slopes:
    sub = df[df['Slope Angle'] == slope]
    for w_idx, w in enumerate(waters):
        for l_idx, lag in enumerate(lags):
            row_data = sub[(sub['Lag'] == lag) & (sub['Water (H, T)'] == w)]
            if row_data.empty: continue

            v = row_data['Velocity'].values[0]
            c = row_data['CoT'].values[0]

            # EXPLICITLY FILTER OUT FAILED OR ZERO-SPEED RUNS
            if v <= 0.0 or c <= 0.0:
                continue

            trace_color = color_map[lag]
            line_dash = dash_map[w]

            # Normalize to the [0, 1] drawing grid
            v_norm = v / v_max
            c_norm = c / c_max

            hover_template = (
                f"<b>Lag: {lag}s</b><br>"
                f"Water: {water_names[w_idx]}<br>"
                f"Slope: {slope}°<br>"
                f"Velocity: {v:.1f} cm/s<br>"
                f"CoT: {c:.1f} P/mgV"
                "<extra></extra>"
            )

            # SPECIAL PLOTTING FOR 19.5 (Trail of Rhombuses)
            if slope == 19.5:
                # Interpolate 12 points across the line
                num_points = 12
                x_vals = np.linspace(0, 1, num_points)
                y_vals = np.linspace(v_norm, c_norm, num_points)

                # Only show text at the first and last points
                text_labels = [f" <b>{v:.1f}</b> <span style='font-size:16px'>(19.5°)</span> "] + [""] * (
                            num_points - 2) + [f" <b>{c:.1f}</b> "]
                text_positions = ['middle left'] + ['top center'] * (num_points - 2) + ['middle right']

                fig.add_trace(go.Scatter(
                    x=x_vals, y=y_vals,
                    mode='lines+markers+text',
                    text=text_labels,
                    textposition=text_positions,
                    textfont=dict(size=22, color=text_color, family="Arial"),
                    # Slightly smaller markers so they don't overlap too much
                    marker=dict(size=24, color=trace_color, symbol='diamond', line=dict(color='white', width=3)),
                    line=dict(color=trace_color, width=8, dash=line_dash),
                    showlegend=False,
                    hovertemplate=hover_template
                ))

            # NORMAL PLOTTING FOR 10.0 (Just Endpoints)
            else:
                fig.add_trace(go.Scatter(
                    x=[0, 1], y=[v_norm, c_norm],
                    mode='lines+markers+text',
                    text=[f" <b>{v:.1f}</b> ", f" <b>{c:.1f}</b> "],
                    textposition=['middle left', 'middle right'],
                    textfont=dict(size=22, color=text_color, family="Arial"),
                    marker=dict(size=32, color=trace_color, symbol='circle', line=dict(color='white', width=4)),
                    line=dict(color=trace_color, width=10, dash=line_dash),
                    showlegend=False,
                    hovertemplate=hover_template
                ))

# ==========================================
# 4. PRO UNIFIED LEGEND SETUP (DUMMY TRACES)
# ==========================================
# Legend Items for Lag (Colors)
for lag in lags:
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='lines+markers',
        marker=dict(size=28, color=color_map[lag], symbol='circle', line=dict(color='white', width=4)),
        line=dict(color=color_map[lag], width=10, dash='solid'),
        name=f"<b>Lag:</b> {lag}s &nbsp;&nbsp;",
        showlegend=True
    ))

# Legend Items for Water (Dash Patterns)
for w_idx, w in enumerate(waters):
    fig.add_trace(go.Scatter(
        x=[None], y=[None], mode='lines',
        line=dict(color=text_color, width=8, dash=dash_map[w]),
        name=f"<b>Water:</b> {water_names[w_idx]} &nbsp;&nbsp;",
        showlegend=True
    ))

# Legend Items for Slope (Marker Symbol)
fig.add_trace(go.Scatter(
    x=[None], y=[None], mode='markers',
    marker=dict(size=24, color=text_color, symbol='circle', line=dict(color='white', width=3)),
    name=f"<b>Slope:</b> 10.0° &nbsp;&nbsp;",
    showlegend=True
))
fig.add_trace(go.Scatter(
    x=[None], y=[None], mode='markers',
    # Update legend to show the multi-rhombus concept
    marker=dict(size=24, color=text_color, symbol='diamond', line=dict(color='white', width=3)),
    name=f"<b>Slope:</b> 19.5° (Rhombus Trail) &nbsp;&nbsp;",
    showlegend=True
))

# ==========================================
# 5. GLOBAL LAYOUT STYLING
# ==========================================
fig.update_layout(
    width=1600, height=1000,
    plot_bgcolor='white', paper_bgcolor='white',

    title=dict(
        text="<b>Velocity to CoT Efficiency Corridors (10.0° & 19.5°)</b>",
        font=dict(size=48, color=text_color, family="Arial"), x=0.5, y=0.97
    ),

    legend=dict(
        orientation="h", yanchor="top", y=-0.08, xanchor="center", x=0.5,
        font=dict(size=24, color=text_color, family="Arial"),
        bgcolor='white', bordercolor=grid_color, borderwidth=4, itemwidth=40
    ),

    margin=dict(l=250, r=250, t=180, b=150)
)

fig.update_xaxes(visible=False, range=[-0.4, 1.4])
fig.update_yaxes(visible=False, range=[-0.05, 1.15])

try:
    fig.write_image('LiquidGlass_Slopegraph_RhombusTrail.svg', format='svg')
    print("SVG successfully saved!")
except Exception as e:
    print(f"Error saving SVG: {e}")

fig.write_html('LiquidGlass_Slopegraph_RhombusTrail.html')
fig.show()