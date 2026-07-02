import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import warnings

warnings.filterwarnings('ignore')

# 1. Read Data
df = pd.read_csv("FinalExp_Ground - Лист1.csv")

cols_to_convert = ['Vel (cm/s)', 'CoT', 'Lag']
for col in cols_to_convert:
    if col in df.columns and df[col].dtype == object:
        df[col] = df[col].astype(str).str.replace(',', '.')

df['Vel_num'] = pd.to_numeric(df['Vel (cm/s)'], errors='coerce')
df['CoT_num'] = pd.to_numeric(df['CoT'], errors='coerce').abs()

# --- Identify Special Categories ---
df['is_unst_vel'] = df['Vel (cm/s)'].astype(str).str.lower().str.contains('unst') | df['Vel_num'].isna()
df['is_unst_cot'] = df['CoT'].astype(str).str.lower().str.contains('unst') | df['CoT_num'].isna()
df['is_outlier_cot'] = df['CoT_num'].abs() > 100
df['is_neg_vel'] = df['Vel_num'] < 0

# Convert special cases to NaN so they don't skew heatmaps
df.loc[df['is_unst_vel'], 'Vel_num'] = np.nan
df.loc[df['is_unst_cot'] | df['is_outlier_cot'], 'CoT_num'] = np.nan


# --- CALCULATE HARMONIC MEAN ---
def calc_hm(row):
    v = abs(row['Vel_num']) if pd.notna(row['Vel_num']) else np.nan
    c = row['CoT_num'] if pd.notna(row['CoT_num']) else np.nan
    if pd.isna(v) or pd.isna(c) or v == 0 or c == 0:
        return np.nan
    inv_c = 1.0 / c
    return 2 * v * inv_c / (v + inv_c)


df['HM_num'] = df.apply(calc_hm, axis=1)


# --- Custom Text Formatting Functions ---
def format_vel_heatmap(row):
    if row['is_unst_vel']: return '<span style="color:white">Unstable</span>'
    v = row['Vel_num']
    if pd.isna(v): return ""
    return f"{v:.4f}" if abs(v) < 0.01 and v != 0 else f"{v:.2f}"


def format_cot_heatmap(row):
    if row['is_unst_cot']: return '<span style="color:white">Unstable</span>'
    if row['is_outlier_cot']: return '<span style="color:white">Outlier</span>'
    c = row['CoT_num']
    if pd.isna(c): return ""
    txt = f"{c:.4f}" if abs(c) < 0.01 and c != 0 else f"{c:.2f}"
    if row['is_neg_vel']: txt += "<br>(Neg Vel)"
    return txt


def format_hm_heatmap(row):
    if row['is_unst_vel'] or row['is_unst_cot']: return '<span style="color:white">Unstable</span>'
    if row['is_outlier_cot']: return '<span style="color:white">Outlier</span>'
    hm = row['HM_num']
    if pd.isna(hm): return ""
    txt = f"{hm:.4f}" if abs(hm) < 0.01 and hm != 0 else f"{hm:.2f}"
    if row['is_neg_vel']: txt += "<br>(Neg Vel)"
    return txt


df['Vel_text_hm'] = df.apply(format_vel_heatmap, axis=1)
df['CoT_text_hm'] = df.apply(format_cot_heatmap, axis=1)
df['HM_text_hm'] = df.apply(format_hm_heatmap, axis=1)

df['Amplitude'] = df['Amplitude'].astype(str)
df['Lag'] = df['Lag'].astype(str)
df['Water (H, T)'] = df['Water (H, T)'].astype(str)

# EXPLICIT ORDERING
waters = ['(100, 0)', '(50, 50)', '(0, 100)']

# ==========================================
# PUBLICATION DESIGN STANDARDS
# ==========================================
# Reverted title to Arial
title_font = dict(family="Arial, sans-serif", size=48, color="#000000")
axis_font = dict(family="Arial, sans-serif", size=40, color="#000000")
tick_font = dict(family="Arial, sans-serif", size=30, color="#000000")
legend_font = dict(family="Arial, sans-serif", size=35, color="#000000")

publication_layout = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=axis_font,
    title_font=title_font,
    # Adjusted margins to balance title gap and give the axes room to breathe
    margin=dict(l=120, r=40, t=150, b=220),
    legend=dict(
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='black',
        borderwidth=1.5,
        font=legend_font
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


# --- HEATMAP ---
def create_heatmap(value_col, text_col, title, colorscale, file_prefix, zmid=None):
    subplot_titles = [f"Water: {w}" for w in waters]
    fig = make_subplots(
        rows=1, cols=len(waters),
        subplot_titles=subplot_titles,
        shared_yaxes=True,
        horizontal_spacing=0.08  # Increased for breathing room
    )

    for i, w in enumerate(waters):
        d = df[df['Water (H, T)'] == w]
        pivot_num = d.pivot(index='Amplitude', columns='Lag', values=value_col)
        pivot_text = d.pivot(index='Amplitude', columns='Lag', values=text_col)
        zmax, zmin = d[value_col].max(), d[value_col].min()

        if zmid == 0 and pd.notna(zmin) and zmin < 0:
            limit = max(abs(zmin), abs(zmax))
            zmin_val, zmax_val = -limit, limit
        else:
            zmin_val, zmax_val = None, None

        fig.add_trace(go.Heatmap(
            z=pivot_num.values, x=pivot_num.columns, y=pivot_num.index,
            coloraxis="coloraxis", text=pivot_text.values, texttemplate="%{text}",
            textfont=dict(family="Arial, sans-serif", size=32),
            zmin=zmin_val, zmax=zmax_val, xgap=1, ygap=1
        ), row=1, col=i + 1)

        fig.update_xaxes(**common_xaxis, row=1, col=i + 1)
        fig.update_xaxes(title_text="Lag", showgrid=False, row=1, col=i + 1)

        fig.update_yaxes(**common_yaxis, row=1, col=i + 1)
        fig.update_yaxes(showgrid=False, row=1, col=i + 1)
        if i == 0:
            fig.update_yaxes(title_text="Amplitude", row=1, col=i + 1)

    layout_args = dict(
        coloraxis=dict(
            colorscale=colorscale,
            colorbar=dict(
                tickfont=tick_font,
                title_font=axis_font,
                outlinewidth=2,
                outlinecolor='black'
            )
        ),
        title=dict(text=title, font=title_font, x=0.5, xanchor='center'),
        width=1900, height=850,  # Slightly wider
        **publication_layout
    )

    layout_args['plot_bgcolor'] = 'black'

    if zmid is not None:
        layout_args['coloraxis']['cmid'] = zmid

    fig.update_layout(**layout_args)

    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="Arial, sans-serif", size=40, color="#000000")

    fig.write_html(f'{file_prefix}_heatmap.html')
    try:
        fig.write_image(f'{file_prefix}_heatmap.png')
    except:
        pass


# --- VERTICAL BARCHART ---
def create_plotly_barchart(value_col, title, file_prefix, ylabel):
    df_plot = df[df[value_col].notna()].copy()

    try:
        amplitudes = sorted(df_plot['Amplitude'].unique(), key=lambda x: float(x))
    except:
        amplitudes = sorted(df_plot['Amplitude'].unique())
    lags = sorted(df_plot['Lag'].unique())

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

    fig = make_subplots(
        rows=1, cols=len(waters),
        subplot_titles=[f"Water: {w}" for w in waters],
        shared_yaxes=True,
        horizontal_spacing=0.08  # Increased for breathing room
    )

    max_val = df_plot[value_col].max()
    min_val = min(df_plot[value_col].min(), 0)
    y_range = [min_val * 1.1 if min_val < 0 else 0, max_val * 1.35]

    for i, w in enumerate(waters):
        d = df_plot[df_plot['Water (H, T)'] == w]
        for lag_idx, lag in enumerate(lags):
            lag_data, text_data = [], []
            for amp in amplitudes:
                subset = d[(d['Amplitude'] == str(amp)) & (d['Lag'] == lag)]
                if len(subset) > 0:
                    val = subset[value_col].iloc[0]
                    lag_data.append(val)

                    row = subset.iloc[0]
                    txt = f'{val:.4f}' if abs(val) < 0.01 and val != 0 else f'{val:.2f}'
                    if (value_col in ['CoT_num', 'HM_num']) and row.get('is_neg_vel', False):
                        txt += '*'
                    text_data.append(txt)
                else:
                    lag_data.append(0)
                    text_data.append("")

            fig.add_trace(go.Bar(
                x=amplitudes, y=lag_data,
                name=f'Lag {lag}',
                text=text_data,
                textposition='outside',
                textangle=-90,
                textfont=dict(family="Arial, sans-serif", size=28, color="black"),
                constraintext='none',  # STOPS PLOTLY FROM AUTO-SHRINKING TEXT
                cliponaxis=False,
                marker_color=colors[lag_idx % len(colors)],
                marker_line=dict(width=2, color='black'),
                showlegend=(i == 0)
            ), row=1, col=i + 1)

        fig.update_xaxes(**common_xaxis, row=1, col=i + 1)
        fig.update_xaxes(title_text="Amplitude", type='category', row=1, col=i + 1)

        fig.update_yaxes(**common_yaxis, row=1, col=i + 1)
        fig.update_yaxes(range=y_range, row=1, col=i + 1)

        if i == 0:
            fig.update_yaxes(title_text=ylabel, row=1, col=i + 1)

    fig.update_layout(
        barmode='group',
        title=dict(text=title, font=title_font, x=0.5, xanchor='center'),
        width=1900, height=900,  # Increased height/width for breathing room
        **publication_layout
    )

    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="Arial, sans-serif", size=40, color="#000000")

    if value_col in ['CoT_num', 'HM_num']:
        fig.add_annotation(
            x=0.5, y=-0.32, xref="paper", yref="paper",  # Pushed lower due to bigger margins
            text="* Values computed from negative velocity",
            showarrow=False, font=dict(family="Arial, sans-serif", size=24, color="gray")
        )

    fig.write_html(f'{file_prefix}_barchart.html')
    try:
        fig.write_image(f'{file_prefix}_barchart.png')
    except:
        pass


# --- HORIZONTAL BARCHART ---
def create_plotly_horizontal_barchart(value_col, title, file_prefix, xlabel):
    df_plot = df[df[value_col].notna()].copy()

    try:
        amplitudes = sorted(df_plot['Amplitude'].unique(), key=lambda x: float(x))
    except:
        amplitudes = sorted(df_plot['Amplitude'].unique())
    lags = sorted(df_plot['Lag'].unique())

    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6']

    fig = make_subplots(
        rows=len(waters), cols=1,
        subplot_titles=[f"Water: {w}" for w in waters],
        shared_xaxes=True,
        vertical_spacing=0.12  # Increased for breathing room
    )

    max_val = df_plot[value_col].max()
    min_val = min(df_plot[value_col].min(), 0)
    x_range = [min_val * 1.1 if min_val < 0 else 0, max_val * 1.35]

    for i, w in enumerate(waters):
        d = df_plot[df_plot['Water (H, T)'] == w]
        for lag_idx, lag in enumerate(lags):
            lag_data, text_data = [], []
            for amp in amplitudes:
                subset = d[(d['Amplitude'] == str(amp)) & (d['Lag'] == lag)]
                if len(subset) > 0:
                    val = subset[value_col].iloc[0]
                    lag_data.append(val)

                    row = subset.iloc[0]
                    txt = f'{val:.4f}' if abs(val) < 0.01 and val != 0 else f'{val:.2f}'
                    if (value_col in ['CoT_num', 'HM_num']) and row.get('is_neg_vel', False):
                        txt += '*'
                    text_data.append(txt)
                else:
                    lag_data.append(0)
                    text_data.append("")

            fig.add_trace(go.Bar(
                y=amplitudes, x=lag_data,
                orientation='h',
                name=f'Lag {lag}',
                text=text_data,
                textposition='outside',
                textfont=dict(family="Arial, sans-serif", size=28, color="black"),
                constraintext='none',  # STOPS PLOTLY FROM AUTO-SHRINKING TEXT
                cliponaxis=False,
                marker_color=colors[lag_idx % len(colors)],
                marker_line=dict(width=2, color='black'),
                showlegend=(i == 0)
            ), row=i + 1, col=1)

        fig.update_xaxes(**common_xaxis, row=i + 1, col=1)
        fig.update_xaxes(range=x_range, row=i + 1, col=1)

        if i == len(waters) - 1:
            fig.update_xaxes(title_text=xlabel, row=i + 1, col=1)

        fig.update_yaxes(**common_yaxis, row=i + 1, col=1)
        fig.update_yaxes(title_text="Amplitude", type='category', row=i + 1, col=1)

    fig.update_layout(
        barmode='group',
        title=dict(text=title, font=title_font, x=0.5, xanchor='center'),
        width=1500, height=1300,  # Increased height/width for breathing room
        **publication_layout
    )

    for annotation in fig['layout']['annotations']:
        annotation['font'] = dict(family="Arial, sans-serif", size=40, color="#000000")

    if value_col in ['CoT_num', 'HM_num']:
        fig.add_annotation(
            x=0.5, y=-0.15, xref="paper", yref="paper",
            text="* Values computed from negative velocity",
            showarrow=False, font=dict(family="Arial, sans-serif", size=24, color="gray")
        )

    fig.write_html(f'{file_prefix}_horizontal_barchart.html')
    try:
        fig.write_image(f'{file_prefix}_horizontal_barchart.png')
    except:
        pass


# --- Execution ---

# 1. Velocity
create_heatmap('Vel_num', 'Vel_text_hm', 'Velocity (cm/s) Faceted Heatmap', 'RdBu', 'vel', zmid=0)
create_plotly_barchart('Vel_num', 'Velocity (cm/s) by Amplitude & Lag', 'vel', 'Velocity (cm/s)')
create_plotly_horizontal_barchart('Vel_num', 'Velocity (cm/s) by Amplitude & Lag', 'vel', 'Velocity (cm/s)')

# 2. Cost of Transport
create_heatmap('CoT_num', 'CoT_text_hm', 'Cost of Transport (CoT) Faceted Heatmap', 'Spectral', 'cot')
create_plotly_barchart('CoT_num', 'Cost of Transport (CoT) by Amplitude & Lag', 'cot', 'Cost of Transport')
create_plotly_horizontal_barchart('CoT_num', 'Cost of Transport (CoT) by Amplitude & Lag', 'cot', 'Cost of Transport')

# 3. Harmonic Mean
create_heatmap('HM_num', 'HM_text_hm', 'Harmonic Mean (Vel & 1/CoT) Faceted Heatmap', 'Viridis', 'hm')
create_plotly_barchart('HM_num', 'Harmonic Mean by Amplitude & Lag', 'hm', 'Harmonic Mean')
create_plotly_horizontal_barchart('HM_num', 'Harmonic Mean by Amplitude & Lag', 'hm', 'Harmonic Mean')