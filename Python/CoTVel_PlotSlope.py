import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
import warnings

warnings.filterwarnings('ignore')

# Set style for beautiful plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

# 1. Read Data
df = pd.read_csv("FinalExp_Ground_Slope - Лист1.csv")

# Clean commas for specific columns
cols_to_convert = ['Vel (cm/s)', 'CoT (P/mgV)', 'Lag', 'Slope Angle', 'Stable?']
for col in cols_to_convert:
    if col in df.columns and df[col].dtype == object:
        df[col] = df[col].astype(str).str.replace(',', '.')

# Parse numeric
df['Vel_num'] = pd.to_numeric(df['Vel (cm/s)'], errors='coerce')
df['CoT_num'] = pd.to_numeric(df['CoT (P/mgV)'], errors='coerce').abs()


# Identify categorical features
def check_cat(val, cat):
    return str(val).strip().upper() == cat


df['is_failed_vel'] = df['Vel (cm/s)'].apply(lambda x: check_cat(x, 'F'))
df['is_steady_vel'] = df['Vel (cm/s)'].apply(lambda x: check_cat(x, 'S'))
df['is_unst_vel'] = df['Vel (cm/s)'].astype(str).str.lower().str.contains('unst')

df['is_failed_cot'] = df['CoT (P/mgV)'].apply(lambda x: check_cat(x, 'F'))
df['is_steady_cot'] = df['CoT (P/mgV)'].apply(lambda x: check_cat(x, 'S'))
df['is_unst_cot'] = df['CoT (P/mgV)'].astype(str).str.lower().str.contains('unst')

df['is_outlier_cot'] = df['CoT_num'].abs() > 100
df['is_neg_vel'] = df['Vel_num'] < 0

# Check for partial stability (50) to attach the asterisk (*) later
df['is_half_stable'] = df['Stable?'].astype(str).str.strip() == '50'
df['is_half_stable'] = df['is_half_stable'] | (df['Stable?'].astype(str).str.strip() == '50.0')

# Convert special cases to NaN so they don't skew heatmaps/bars
invalid_vel = df['is_failed_vel'] | df['is_steady_vel'] | df['is_unst_vel']
invalid_cot = df['is_failed_cot'] | df['is_steady_cot'] | df['is_unst_cot'] | df['is_outlier_cot']

df.loc[invalid_vel, 'Vel_num'] = np.nan
df.loc[invalid_cot, 'CoT_num'] = np.nan


# --- CALCULATE HARMONIC MEAN ---
def calc_hm(row):
    v = abs(row['Vel_num']) if pd.notna(row['Vel_num']) else np.nan
    c = row['CoT_num'] if pd.notna(row['CoT_num']) else np.nan
    if pd.isna(v) or pd.isna(c) or v == 0 or c == 0: return np.nan
    inv_c = 1.0 / c
    return 2 * v * inv_c / (v + inv_c)


df['HM_num'] = df.apply(calc_hm, axis=1)


# --- Custom Text Formatting Functions ---
def format_text(row, val_col, is_failed, is_steady, is_unst, is_outlier, is_vel=False):
    if is_failed: return '<span style="color:white">Failed</span>'
    if is_steady: return '<span style="color:white">Steady</span>'
    if is_unst: return '<span style="color:white">Unstable</span>'
    if is_outlier: return '<span style="color:white">Outlier</span>'

    v = row[val_col]
    if pd.isna(v): return ""
    txt = f"{v:.4f}" if abs(v) < 0.01 and v != 0 else f"{v:.2f}"

    if not is_vel and row['is_neg_vel']: txt += "<br>(Neg Vel)"
    if row['is_half_stable']: txt += "*"
    return txt


df['Vel_text_hm'] = df.apply(
    lambda r: format_text(r, 'Vel_num', r['is_failed_vel'], r['is_steady_vel'], r['is_unst_vel'], False, True), axis=1)
df['CoT_text_hm'] = df.apply(
    lambda r: format_text(r, 'CoT_num', r['is_failed_cot'], r['is_steady_cot'], r['is_unst_cot'], r['is_outlier_cot'],
                          False), axis=1)
df['HM_text_hm'] = df.apply(lambda r: format_text(r, 'HM_num', r['is_failed_vel'] or r['is_failed_cot'],
                                                  r['is_steady_vel'] or r['is_steady_cot'],
                                                  r['is_unst_vel'] or r['is_unst_cot'], r['is_outlier_cot'], False),
                            axis=1)

df['Slope Angle'] = df['Slope Angle'].astype(str)
df['Lag'] = df['Lag'].astype(str)
df['Water (H, T)'] = df['Water (H, T)'].astype(str)

waters = df['Water (H, T)'].unique().tolist()


# --- Heatmap Plotting ---
def create_heatmap(value_col, text_col, title, colorscale, file_prefix, zmid=None):
    # Use HTML span styling to make subplot titles much bigger
    subplot_titles = [f"<span style='font-size: 40px;'>Water: {w}</span>" for w in waters]

    fig = make_subplots(rows=1, cols=len(waters), subplot_titles=subplot_titles, shared_yaxes=True,
                        horizontal_spacing=0.05)

    for i, w in enumerate(waters):
        d = df[df['Water (H, T)'] == w]
        pivot_num = d.pivot(index='Slope Angle', columns='Lag', values=value_col)
        pivot_text = d.pivot(index='Slope Angle', columns='Lag', values=text_col)

        zmax = d[value_col].max()
        zmin = d[value_col].min()
        zmin_val, zmax_val = None, None
        if zmid == 0 and pd.notna(zmin) and zmin < 0:
            limit = max(abs(zmin), abs(zmax))
            zmin_val, zmax_val = -limit, limit

        fig.add_trace(
            go.Heatmap(z=pivot_num.values, x=pivot_num.columns, y=pivot_num.index,
                       coloraxis="coloraxis", text=pivot_text.values, texttemplate="%{text}",
                       textfont=dict(size=24), zmin=zmin_val, zmax=zmax_val, xgap=1, ygap=1),
            row=1, col=i + 1
        )

        # Add gray rectangles for Steady cells dynamically
        for y_idx, y_val in enumerate(pivot_text.index):
            for x_idx, x_val in enumerate(pivot_text.columns):
                txt = pivot_text.loc[y_val, x_val]
                if isinstance(txt, str) and 'Steady' in txt:
                    fig.add_shape(
                        type="rect",
                        x0=x_idx - 0.5, x1=x_idx + 0.5,
                        y0=y_idx - 0.5, y1=y_idx + 0.5,
                        fillcolor="gray",
                        line=dict(width=0),
                        layer="below",  # Drawn below the text but acts as a background for empty NaN spots
                        row=1, col=i + 1
                    )

        fig.update_xaxes(title_text="Lag", row=1, col=i + 1, showgrid=False)
        if i == 0: fig.update_yaxes(title_text="Slope Angle", row=1, col=i + 1, showgrid=False)

    layout_args = dict(coloraxis=dict(colorscale=colorscale), title=title, font=dict(size=24), height=650, width=1600,
                       plot_bgcolor='black')
    if zmid is not None: layout_args['coloraxis']['cmid'] = zmid
    fig.update_layout(**layout_args)

    # Optional: Increase the main title font size too!
    fig.update_layout(title_font_size=32)

    fig.write_html(f'{file_prefix}_heatmap.html')
    try:
        fig.write_image(f'{file_prefix}_heatmap.png')
    except:
        pass


# --- Barchart Plotting ---
def create_beautiful_barchart(value_col, title, file_prefix, ylabel):
    df_plot = df[df[value_col].notna()].copy()
    try:
        slopes = sorted(df_plot['Slope Angle'].unique(), key=lambda x: float(x))
    except:
        slopes = sorted(df_plot['Slope Angle'].unique())

    lags = sorted(df_plot['Lag'].unique())
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

    fig, axes = plt.subplots(1, len(waters), figsize=(max(7, 7 * len(waters)), 7), sharey=True, squeeze=False)
    axes = axes[0]
    fig.suptitle(title, fontsize=22, fontweight='bold', y=0.98)

    for idx, water in enumerate(waters):
        ax = axes[idx]
        d = df_plot[df_plot['Water (H, T)'] == water]
        x = np.arange(len(slopes))
        width = 0.8 / len(lags) if len(lags) > 0 else 0.25
        multiplier = 0

        for lag_idx, lag in enumerate(lags):
            lag_data = []
            for slp in slopes:
                subset = d[(d['Slope Angle'] == slp) & (d['Lag'] == lag)]
                lag_data.append(subset[value_col].iloc[0] if len(subset) > 0 else 0)

            offset = width * multiplier
            bars = ax.bar(x + offset, lag_data, width, label=f'Lag {lag}', color=colors[lag_idx % len(colors)],
                          edgecolor='white', linewidth=1.5, alpha=0.9)

            for bar, val in zip(bars, lag_data):
                if val != 0:
                    height = bar.get_height()
                    label_y = height + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02
                    slp_val = slopes[bars.index(bar)]
                    subset = d[(d['Slope Angle'] == slp_val) & (d['Lag'] == lag)]

                    if len(subset) > 0:
                        row = subset.iloc[0]
                        label_text = f'{val:.4f}' if abs(val) < 0.01 and val != 0 else f'{val:.2f}'
                        if value_col in ['CoT_num', 'HM_num'] and row.get('is_neg_vel',
                                                                          False): label_text += '\n(Neg Vel)'

                        if row.get('is_half_stable', False): label_text += '*'

                        ax.text(bar.get_x() + bar.get_width() / 2, label_y, label_text, ha='center', va='bottom',
                                fontsize=9, fontweight='bold')
            multiplier += 1

        ax.set_xlabel('Slope Angle', fontsize=14, fontweight='bold')
        if idx == 0: ax.set_ylabel(ylabel, fontsize=14, fontweight='bold')
        ax.set_title(f'Water {water}', fontsize=16, fontweight='bold', pad=15)
        ax.set_xticks(x + (width * (len(lags) - 1) / 2))
        ax.set_xticklabels(slopes, fontsize=12)
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.8)
        ax.set_axisbelow(True)
        if idx == 0: ax.legend()
        ax.set_facecolor('#F8F9FA')

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])
    plt.savefig(f'{file_prefix}_barchart.png', dpi=300, bbox_inches='tight')
    plt.close()


# --- Execution ---
create_heatmap('Vel_num', 'Vel_text_hm', 'Velocity (cm/s) Faceted Heatmap', 'RdBu', 'vel', zmid=0)
create_beautiful_barchart('Vel_num', 'Velocity (cm/s) by Slope & Lag', 'vel', 'Velocity (cm/s)')

create_heatmap('CoT_num', 'CoT_text_hm', 'Cost of Transport (CoT) Faceted Heatmap', 'Spectral', 'cot')
create_beautiful_barchart('CoT_num', 'Cost of Transport (CoT) by Slope & Lag', 'cot', 'Cost of Transport')

create_heatmap('HM_num', 'HM_text_hm', 'Harmonic Mean (Vel & 1/CoT) Faceted Heatmap', 'Viridis', 'hm')
create_beautiful_barchart('HM_num', 'Harmonic Mean by Slope & Lag', 'hm', 'Harmonic Mean')