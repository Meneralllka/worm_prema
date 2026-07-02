import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')

# ==========================================
# 1. READ AND PREPROCESS DATA
# ==========================================
df = pd.read_csv("FinalExp_Water - Лист1.csv")

# Clean numeric columns
df['Amplitude'] = df['Amplitude'].astype(float)
df['Lag'] = df['Lag'].astype(str).str.replace(',', '.').astype(float)
df['Vel (cm/s)'] = df['Vel (cm/s)'].astype(str).str.replace(',', '.')
df['CoT (P/mgV)'] = df['CoT (P/mgV)'].astype(str).str.replace(',', '.')

# Isolate Lag 1.2s
df_12 = df[df['Lag'] == 1.2].copy()


def parse_val(v):
    if v == 'F': return np.nan
    try:
        return float(v)
    except:
        return np.nan


df_12['Velocity'] = df_12['Vel (cm/s)'].apply(parse_val)
df_12['CoT'] = df_12['CoT (P/mgV)'].apply(parse_val)

waters = ['(100, 0)', '(50, 50)', '(0, 100)']
water_names = ['Head Heavy', 'Balanced', 'Tail Heavy']

# High-contrast "Liquid Glass" palette
colors = ['rgba(56, 189, 248, 0.95)',  # Sky Blue
          'rgba(236, 72, 153, 0.95)',  # Magenta
          'rgba(251, 146, 60, 0.95)']  # Vibrant Orange

shadow_color = 'rgba(0,0,0,0.15)'

# ==========================================
# 2. BUILD THE PARETO BUBBLE MATRIX
# ==========================================
fig = go.Figure()

for i, w in enumerate(waters):
    # Drop failures (like Tail Heavy @ Amp 20) and sort by Amplitude
    sub = df_12[df_12['Water (H, T)'] == w].dropna(subset=['Velocity', 'CoT']).sort_values('Amplitude')

    # Base sizes for the bubbles mapped to Amplitude
    sizes = sub['Amplitude'] * 1.5

    # A. The Flow Line (Connecting the amplitudes)
    fig.add_trace(go.Scatter(
        x=sub['Velocity'], y=sub['CoT'],
        mode='lines',
        line=dict(color=colors[i].replace('0.95', '0.6'), width=8, shape='spline'),
        hoverinfo='skip', showlegend=False
    ))

    # B. Liquid Glass Drop Shadows (Offset down and right)
    fig.add_trace(go.Scatter(
        x=sub['Velocity'] + 0.04, y=sub['CoT'] + 0.015,  # Note: Y is reversed, so + is down
        mode='markers',
        marker=dict(size=sizes, color=shadow_color),
        hoverinfo='skip', showlegend=False
    ))

    # C. Main Glass Orbs
    fig.add_trace(go.Scatter(
        x=sub['Velocity'], y=sub['CoT'],
        mode='markers+text',
        name=f"<b>{water_names[i]}</b>",
        text=[f"<b>{int(a)}</b>" for a in sub['Amplitude']],
        textposition="middle center",
        textfont=dict(color="white", size=24, family="Arial"),
        marker=dict(size=sizes, color=colors[i], line=dict(color='white', width=4))
    ))

# ==========================================
# 3. LAYOUT & ANNOTATIONS
# ==========================================
fig.update_layout(
    title=dict(text="<b>Lag 1.2s: The Pareto Efficiency Frontier</b>",
               font=dict(size=54, color="#1e293b", family="Arial"), x=0.5, y=0.95),
    width=2400, height=1400, plot_bgcolor='white', paper_bgcolor='white',
    legend=dict(title="<b>Water Placement</b>", orientation="h", yanchor="top", y=-0.10, xanchor="center", x=0.5,
                font=dict(size=36, color="#1e293b"), bgcolor='white', bordercolor='#cbd5e1', borderwidth=4,
                itemwidth=120)
)

# X-Axis: Velocity
fig.update_xaxes(
    title="<b>Velocity (cm/s)</b> ➔ (Faster is Better)", title_font=dict(size=36, color="#1e293b"),
    tickfont=dict(size=28, color="#1e293b"), gridcolor='#cbd5e1', gridwidth=2,
    showline=True, linewidth=4, linecolor='#cbd5e1', range=[-0.2, 6.8]
)

# Y-Axis: Cost of Transport (REVERSED so Top = Better)
fig.update_yaxes(
    title="<b>Cost of Transport (P/mgV)</b> ➔ (Lower is Better)", title_font=dict(size=36, color="#1e293b"),
    tickfont=dict(size=28, color="#1e293b"), gridcolor='#cbd5e1', gridwidth=2,
    showline=True, linewidth=4, linecolor='#cbd5e1',
    autorange="reversed", range=[1.15, 0.05]
)

# Highlight "Optimal Zone" Box
fig.add_shape(
    type="rect", x0=4.5, x1=6.5, y0=0.25, y1=0.08,
    fillcolor="rgba(34, 197, 94, 0.05)", line=dict(color="rgba(34, 197, 94, 0.5)", width=4, dash="dash"), layer="below"
)

# Text Annotations
fig.add_annotation(
    x=5.5, y=0.22, xref="x", yref="y", text="<b>Optimal Zone</b>",
    showarrow=False, font=dict(size=36, color="rgba(34, 197, 94, 1.0)", family="Arial"), align="center"
)

fig.add_annotation(
    x=5.0, y=0.129, xref="x", yref="y", text="<b>Most Efficient</b>",
    showarrow=True, arrowhead=2, arrowsize=2, arrowwidth=4, arrowcolor="#1e293b", ax=-150, ay=0,
    font=dict(size=28, color="#1e293b", family="Arial")
)

fig.add_annotation(
    x=6.0, y=0.155, xref="x", yref="y", text="<b>Absolute Fastest</b>",
    showarrow=True, arrowhead=2, arrowsize=2, arrowwidth=4, arrowcolor="#1e293b", ax=0, ay=120,
    font=dict(size=28, color="#1e293b", family="Arial")
)

fig.write_html('pareto_liquid_glass.html')
fig.show()