import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import matplotlib.pyplot as plt
import seaborn as sns
from matplotlib.patches import Rectangle
import warnings

warnings.filterwarnings('ignore')

# Set style for beautiful plots
plt.style.use('seaborn-v0_8-darkgrid')
sns.set_palette("husl")

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

# Convert special cases to NaN so they don't skew heatmaps (rendering as transparent/black)
df.loc[df['is_unst_vel'], 'Vel_num'] = np.nan
df.loc[df['is_unst_cot'] | df['is_outlier_cot'], 'CoT_num'] = np.nan


# --- CALCULATE HARMONIC MEAN ---
def calc_hm(row):
    # Use absolute values for the calculation
    v = abs(row['Vel_num']) if pd.notna(row['Vel_num']) else np.nan
    c = row['CoT_num'] if pd.notna(row['CoT_num']) else np.nan

    # Avoid div by zero or calculating NaN
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
    # Carry over the negative velocity flag explicitly
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


# --- Heatmap (keeping the original) ---
def create_heatmap(value_col, text_col, title, colorscale, file_prefix, zmid=None):
    fig = make_subplots(
        rows=1, cols=len(waters),
        subplot_titles=[f"Water: {w}" for w in waters],
        shared_yaxes=True,
        horizontal_spacing=0.05
    )

    for i, w in enumerate(waters):
        d = df[df['Water (H, T)'] == w]
        pivot_num = d.pivot(index='Amplitude', columns='Lag', values=value_col)
        pivot_text = d.pivot(index='Amplitude', columns='Lag', values=text_col)

        zmax = d[value_col].max()
        zmin = d[value_col].min()
        if zmid == 0 and pd.notna(zmin) and zmin < 0:
            limit = max(abs(zmin), abs(zmax))
            zmin_val, zmax_val = -limit, limit
        else:
            zmin_val, zmax_val = None, None

        fig.add_trace(
            go.Heatmap(
                z=pivot_num.values,
                x=pivot_num.columns,
                y=pivot_num.index,
                coloraxis="coloraxis",
                text=pivot_text.values,
                texttemplate="%{text}",
                textfont=dict(size=24),
                zmin=zmin_val, zmax=zmax_val,
                xgap=1, ygap=1
            ),
            row=1, col=i + 1
        )

        fig.update_xaxes(title_text="Lag", row=1, col=i + 1, showgrid=False)
        if i == 0:
            fig.update_yaxes(title_text="Amplitude", row=1, col=i + 1, showgrid=False)

    layout_args = dict(
        coloraxis=dict(colorscale=colorscale),
        title=title,
        font=dict(size=24),
        height=600, width=1600,
        plot_bgcolor='black'
    )

    if zmid is not None:
        layout_args['coloraxis']['cmid'] = zmid

    fig.update_layout(**layout_args)
    for annotation in fig.layout.annotations:
        annotation.font.size = 24

    fig.write_html(f'{file_prefix}_heatmap.html')
    try:
        fig.write_image(f'{file_prefix}_heatmap.png')
    except:
        pass


# --- IMPROVED BAR CHARTS using Matplotlib + Seaborn ---
def create_beautiful_barchart(value_col, title, file_prefix, ylabel):
    """
    Create a beautiful grouped bar chart with modern styling
    """
    df_plot = df.copy()
    df_plot = df_plot[df_plot[value_col].notna()].copy()

    amplitudes = sorted(df_plot['Amplitude'].unique(), key=lambda x: int(x))
    lags = sorted(df_plot['Lag'].unique())

    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#FFA07A', '#98D8C8']

    fig, axes = plt.subplots(1, 3, figsize=(20, 7), sharey=True)
    fig.suptitle(title, fontsize=22, fontweight='bold', y=0.98)

    for idx, water in enumerate(waters):
        ax = axes[idx]
        d = df_plot[df_plot['Water (H, T)'] == water]

        x = np.arange(len(amplitudes))
        width = 0.25
        multiplier = 0

        for lag_idx, lag in enumerate(lags):
            lag_data = []
            for amp in amplitudes:
                subset = d[(d['Amplitude'] == amp) & (d['Lag'] == lag)]
                if len(subset) > 0:
                    val = subset[value_col].iloc[0]
                    lag_data.append(val)
                else:
                    lag_data.append(0)

            offset = width * multiplier
            bars = ax.bar(x + offset, lag_data, width, label=f'Lag {lag}',
                          color=colors[lag_idx % len(colors)],
                          edgecolor='white', linewidth=1.5,
                          alpha=0.9)

            for bar, val in zip(bars, lag_data):
                if val != 0:
                    height = bar.get_height()
                    label_y = height + (ax.get_ylim()[1] - ax.get_ylim()[0]) * 0.02

                    amp_val = amplitudes[bars.index(bar)]
                    subset = d[(d['Amplitude'] == amp_val) & (d['Lag'] == lag)]

                    if len(subset) > 0:
                        row = subset.iloc[0]
                        if abs(val) < 0.01 and val != 0:
                            label_text = f'{val:.4f}'
                        else:
                            label_text = f'{val:.2f}'

                        # Add annotation for negative velocity if applicable
                        if (value_col == 'CoT_num' or value_col == 'HM_num') and row.get('is_neg_vel', False):
                            label_text += '*'

                        ax.text(bar.get_x() + bar.get_width() / 2, label_y, label_text,
                                ha='center', va='bottom', fontsize=9, fontweight='bold',
                                rotation=0)

            multiplier += 1

        ax.set_xlabel('Amplitude', fontsize=14, fontweight='bold')
        if idx == 0:
            ax.set_ylabel(ylabel, fontsize=14, fontweight='bold')
        ax.set_title(f'Water {water}', fontsize=16, fontweight='bold', pad=15)
        ax.set_xticks(x + width)
        ax.set_xticklabels(amplitudes, fontsize=12)
        ax.tick_params(axis='y', labelsize=11)
        ax.grid(axis='y', alpha=0.3, linestyle='--', linewidth=0.8)
        ax.set_axisbelow(True)

        if d[value_col].min() < 0:
            ax.axhline(y=0, color='black', linestyle='-', linewidth=1.5, alpha=0.7)

        if idx == 0:
            ax.legend(loc='upper left', fontsize=11, framealpha=0.95,
                      edgecolor='gray', fancybox=True)

        ax.set_facecolor('#F8F9FA')

    # Add footnote for negative velocity markers
    if value_col == 'CoT_num' or value_col == 'HM_num':
        fig.text(0.5, 0.02, '* Values computed from negative velocity',
                 ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout(rect=[0, 0.03, 1, 0.96])

    plt.savefig(f'{file_prefix}_barchart.png', dpi=300, bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.savefig(f'{file_prefix}_barchart.pdf', bbox_inches='tight',
                facecolor='white', edgecolor='none')
    plt.close()


# --- ALTERNATIVE: Horizontal Grouped Bar Chart ---
def create_horizontal_barchart(value_col, title, file_prefix, xlabel):
    """
    Create a horizontal grouped bar chart - easier to read labels
    """
    df_plot = df.copy()
    df_plot = df_plot[df_plot[value_col].notna()].copy()

    fig, axes = plt.subplots(3, 1, figsize=(16, 12), sharex=True)
    fig.suptitle(title, fontsize=22, fontweight='bold', y=0.995)

    colors = ['#E74C3C', '#3498DB', '#2ECC71', '#F39C12', '#9B59B6']

    for idx, water in enumerate(waters):
        ax = axes[idx]
        d = df_plot[df_plot['Water (H, T)'] == water]

        amplitudes = sorted(d['Amplitude'].unique(), key=lambda x: int(x))
        lags = sorted(d['Lag'].unique())

        y = np.arange(len(amplitudes))
        height = 0.25
        multiplier = 0

        for lag_idx, lag in enumerate(lags):
            lag_data = []
            for amp in amplitudes:
                subset = d[(d['Amplitude'] == amp) & (d['Lag'] == lag)]
                if len(subset) > 0:
                    val = subset[value_col].iloc[0]
                    lag_data.append(val)
                else:
                    lag_data.append(0)

            offset = height * multiplier
            bars = ax.barh(y + offset, lag_data, height, label=f'Lag {lag}',
                           color=colors[lag_idx % len(colors)],
                           edgecolor='white', linewidth=1.5, alpha=0.9)

            for bar, val in zip(bars, lag_data):
                if val != 0:
                    width = bar.get_width()
                    label_x = width + (ax.get_xlim()[1] - ax.get_xlim()[0]) * 0.01

                    if abs(val) < 0.01 and val != 0:
                        label_text = f'{val:.4f}'
                    else:
                        label_text = f'{val:.2f}'

                    if value_col == 'CoT_num' or value_col == 'HM_num':
                        amp_val = amplitudes[bars.index(bar)]
                        subset = d[(d['Amplitude'] == amp_val) & (d['Lag'] == lag)]
                        if len(subset) > 0 and subset.iloc[0].get('is_neg_vel', False):
                            label_text += '*'

                    ax.text(label_x, bar.get_y() + bar.get_height() / 2, label_text,
                            ha='left', va='center', fontsize=10, fontweight='bold')

            multiplier += 1

        ax.set_ylabel('Amplitude', fontsize=14, fontweight='bold')
        if idx == 2:
            ax.set_xlabel(xlabel, fontsize=14, fontweight='bold')
        ax.set_title(f'Water {water}', fontsize=16, fontweight='bold',
                     loc='left', pad=10)
        ax.set_yticks(y + height)
        ax.set_yticklabels(amplitudes, fontsize=12)
        ax.tick_params(axis='x', labelsize=11)
        ax.grid(axis='x', alpha=0.3, linestyle='--', linewidth=0.8)
        ax.set_axisbelow(True)

        if d[value_col].min() < 0:
            ax.axvline(x=0, color='black', linestyle='-', linewidth=1.5, alpha=0.7)

        if idx == 0:
            ax.legend(loc='best', fontsize=11, framealpha=0.95,
                      edgecolor='gray', fancybox=True, ncol=3)

        ax.set_facecolor('#F8F9FA')

    if value_col == 'CoT_num' or value_col == 'HM_num':
        fig.text(0.5, 0.01, '* Values computed from negative velocity',
                 ha='center', fontsize=10, style='italic', color='gray')

    plt.tight_layout(rect=[0, 0.02, 1, 0.99])

    plt.savefig(f'{file_prefix}_horizontal_barchart.png', dpi=300,
                bbox_inches='tight', facecolor='white')
    plt.savefig(f'{file_prefix}_horizontal_barchart.pdf',
                bbox_inches='tight', facecolor='white')
    plt.close()


# --- Execution ---

# 1. Velocity
create_heatmap('Vel_num', 'Vel_text_hm', 'Velocity (cm/s) Faceted Heatmap', 'RdBu', 'vel', zmid=0)
create_beautiful_barchart('Vel_num', 'Velocity (cm/s) by Amplitude & Lag', 'vel', 'Velocity (cm/s)')
create_horizontal_barchart('Vel_num', 'Velocity (cm/s) by Amplitude & Lag', 'vel', 'Velocity (cm/s)')

# 2. Cost of Transport
create_heatmap('CoT_num', 'CoT_text_hm', 'Cost of Transport (CoT) Faceted Heatmap', 'Spectral', 'cot')
create_beautiful_barchart('CoT_num', 'Cost of Transport (CoT) by Amplitude & Lag', 'cot', 'Cost of Transport')
create_horizontal_barchart('CoT_num', 'Cost of Transport (CoT) by Amplitude & Lag', 'cot', 'Cost of Transport')

# 3. Harmonic Mean
create_heatmap('HM_num', 'HM_text_hm', 'Harmonic Mean (Vel & 1/CoT) Faceted Heatmap', 'Viridis', 'hm')
create_beautiful_barchart('HM_num', 'Harmonic Mean by Amplitude & Lag', 'hm', 'Harmonic Mean')
create_horizontal_barchart('HM_num', 'Harmonic Mean by Amplitude & Lag', 'hm', 'Harmonic Mean')