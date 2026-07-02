import pandas as pd
import numpy as np
import plotly.graph_objects as go
import warnings

warnings.filterwarnings('ignore')


# --- 1. Helper Function to Read and Clean All 3 Datasets ---
def process_data(file_path, env_name, param_col):
    df = pd.read_csv(file_path)

    # Handle column name variations
    cot_col = 'CoT (P/mgV)' if 'CoT (P/mgV)' in df.columns else 'CoT'
    cols_to_convert = ['Vel (cm/s)', 'Lag', param_col, cot_col]

    for c in cols_to_convert:
        if c in df.columns and df[c].dtype == object:
            df[c] = df[c].astype(str).str.replace(',', '.')

    df['Vel_num'] = pd.to_numeric(df['Vel (cm/s)'], errors='coerce')
    df['CoT_num'] = pd.to_numeric(df[cot_col], errors='coerce').abs()

    # Check text categories (F, S, Unstable)
    def check_cat(val, cat):
        return str(val).strip().upper() == cat

    invalid_v = (df['Vel (cm/s)'].apply(lambda x: check_cat(x, 'F')) |
                 df['Vel (cm/s)'].apply(lambda x: check_cat(x, 'S')) |
                 df['Vel (cm/s)'].astype(str).str.lower().str.contains('unst'))
    invalid_c = (df[cot_col].apply(lambda x: check_cat(x, 'F')) |
                 df[cot_col].apply(lambda x: check_cat(x, 'S')) |
                 df[cot_col].astype(str).str.lower().str.contains('unst') |
                 (df['CoT_num'].abs() > 100))

    df.loc[invalid_v, 'Vel_num'] = np.nan
    df.loc[invalid_c, 'CoT_num'] = np.nan

    # Harmonic Mean
    def calc_hm(row):
        v = abs(row['Vel_num']) if pd.notna(row['Vel_num']) else np.nan
        c = row['CoT_num'] if pd.notna(row['CoT_num']) else np.nan
        if pd.isna(v) or pd.isna(c) or v == 0 or c == 0: return np.nan
        inv_c = 1.0 / c
        return 2 * v * inv_c / (v + inv_c)

    df['HM_num'] = df.apply(calc_hm, axis=1)

    # Standardize names for the unified dataframe
    df['Environment'] = env_name
    df['Config_Param'] = df[param_col].astype(str)
    df['Lag'] = df['Lag'].astype(str)
    df['Param_Name'] = param_col  # Keep track of whether it was Amplitude or Slope

    return df


# --- 2. Load and Combine Data ---
df_ground = process_data("FinalExp_Ground - Лист1.csv", "Ground", "Amplitude")
df_slope = process_data("FinalExp_Ground_Slope - Лист1.csv", "Slope", "Slope Angle")
df_water = process_data("FinalExp_Water - Лист1.csv", "Water", "Amplitude")

df_all = pd.concat([df_ground, df_slope, df_water], ignore_index=True)

# --- 3. FILTER OUT OUTLIERS: Remove Ground points with CoT > 12 ---
df_all = df_all[~((df_all['Environment'] == 'Ground') & (df_all['CoT_num'] > 12))]

# --- 4. Publication-Grade Styling (LARGER FONTS) ---
# Professional color palette - colorblind-safe, print-friendly
colors = {
    'Ground': '#1f77b4',  # Professional blue
    'Slope': '#ff7f0e',  # Orange
    'Water': '#2ca02c'  # Green
}

# Highlight colors for top-5 performers
highlight_colors = {
    'Ground': '#0d3d6b',  # Darker blue
    'Slope': '#c25804',  # Darker orange
    'Water': '#1a6b1a'  # Darker green
}

# Typography - INCREASED SIZES
title_font = dict(family="Arial, sans-serif", size=48, color="#000000")
axis_font = dict(family="Arial, sans-serif", size=40, color="#000000")
tick_font = dict(family="Arial, sans-serif", size=30, color="#000000")
legend_font = dict(family="Arial, sans-serif", size=35, color="#000000")

# Clean, minimal layout matching Science/Nature standards
publication_layout = dict(
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=axis_font,
    title_font=title_font,
    margin=dict(l=120, r=80, t=120, b=100),  # Proper spacing for labels
    legend=dict(
        bgcolor='rgba(255,255,255,0.9)',
        bordercolor='#666666',
        borderwidth=1.5,
        font=legend_font,
        x=0.98,  # TOP RIGHT
        y=0.98,
        xanchor='right',
        yanchor='top'
    )
)

# Axis styling - clean, professional
common_xaxis = dict(
    showline=True,
    linewidth=2.5,
    linecolor='#000000',
    mirror=True,
    ticks='outside',
    tickwidth=2,
    ticklen=6,
    tickcolor='#000000',
    gridcolor='#E5E5E5',
    gridwidth=1,
    showgrid=True,
    zeroline=False,
    tickfont=tick_font,
    title_font=axis_font
)

common_yaxis = dict(
    showline=True,
    linewidth=2.5,
    linecolor='#000000',
    mirror=True,
    ticks='outside',
    tickwidth=2,
    ticklen=6,
    tickcolor='#000000',
    gridcolor='#E5E5E5',
    gridwidth=1,
    showgrid=True,
    zeroline=False,
    tickfont=tick_font,
    title_font=axis_font
)

# =========================================================
# PLOT 1: Performance Trade-off Scatter with Top-5 Highlighted
# =========================================================
df_plot1 = df_all.dropna(subset=['Vel_num', 'CoT_num'])

# Identify top-5 performers by HM for each environment
top5_indices = []
for env in ['Ground', 'Slope', 'Water']:
    env_data = df_plot1[df_plot1['Environment'] == env].copy()
    env_data = env_data.dropna(subset=['HM_num'])
    top5 = env_data.nlargest(5, 'HM_num')
    top5_indices.extend(top5.index.tolist())

df_plot1['is_top5'] = df_plot1.index.isin(top5_indices)

fig1 = go.Figure()

# Add regular points first, then top-5 on top
for is_top in [False, True]:
    for env in ['Ground', 'Slope', 'Water']:
        d = df_plot1[(df_plot1['Environment'] == env) & (df_plot1['is_top5'] == is_top)]
        if len(d) == 0:
            continue

        hover_text = d.apply(
            lambda r: f"{r['Param_Name']}: {r['Config_Param']}<br>Lag: {r['Lag']}<br>HM: {r['HM_num']:.2f}", axis=1)

        trace_name = f"{env}" if not is_top else f"{env} (Top-5)"
        marker_color = highlight_colors[env] if is_top else colors[env]
        marker_size = 40 if is_top else 28
        marker_symbol = 'star' if is_top else 'circle'

        fig1.add_trace(go.Scatter(
            x=d['CoT_num'],
            y=d['Vel_num'],
            mode='markers',
            name=trace_name,
            marker=dict(
                size=marker_size,
                color=marker_color,
                line=dict(width=2, color='#000000'),
                opacity=0.9 if is_top else 0.7,
                symbol=marker_symbol
            ),
            text=hover_text,
            hovertemplate="<b>%{text}</b><br>CoT: %{x:.2f}<br>Velocity: %{y:.2f} cm/s<extra></extra>",
            legendgroup=env,
            showlegend=True
        ))

# Configure axes for scatter plot
xa1 = common_xaxis.copy()
xa1['title'] = dict(text="Cost of Transport (P/mgV)", font=axis_font)

ya1 = common_yaxis.copy()
ya1['title'] = dict(text="Velocity (cm/s)", font=axis_font)

fig1.update_layout(
    title=dict(text="<b>A</b>  Performance landscape across terrains", font=title_font, x=0.02),
    xaxis=xa1,
    yaxis=ya1,
    width=1400,
    height=1000,
    **publication_layout
)

fig1.write_html('Figure1_Performance_Landscape.html')
try:
    fig1.write_image('Figure1_Performance_Landscape.png', scale=3)
    fig1.write_image('Figure1_Performance_Landscape.pdf')
except Exception as e:
    print(f"Image export requires kaleido: {e}")

# =========================================================
# PLOT 2: Best-in-Class Bar Chart (Max HM per Environment)
# =========================================================
best_hm = df_all.loc[df_all.groupby('Environment')['HM_num'].idxmax()].copy()
best_hm['Env_Cat'] = pd.Categorical(best_hm['Environment'], categories=['Ground', 'Slope', 'Water'], ordered=True)
best_hm = best_hm.sort_values('Env_Cat')

# Create clean annotations for parameters
best_hm['Param_Label'] = best_hm.apply(
    lambda r: f"{r['Config_Param']} {r['Param_Name'].lower()}, lag {r['Lag']}",
    axis=1
)

fig2 = go.Figure()

# Add bars
fig2.add_trace(go.Bar(
    x=best_hm['Environment'],
    y=best_hm['HM_num'],
    marker=dict(
        color=[colors[e] for e in best_hm['Environment']],
        line=dict(width=2, color='#000000'),
        opacity=0.85
    ),
    width=0.6,
    hovertemplate="<b>%{x}</b><br>Harmonic Mean: %{y:.2f}<extra></extra>"
))

# Add value labels on top of bars
for idx, row in best_hm.iterrows():
    fig2.add_annotation(
        x=row['Environment'],
        y=row['HM_num'],
        text=f"<b>{row['HM_num']:.1f}</b>",
        showarrow=False,
        yshift=20,
        font=dict(size=28, color='#000000', family="Arial, sans-serif")
    )

    # Add parameter info below x-axis
    fig2.add_annotation(
        x=row['Environment'],
        y=0,
        text=row['Param_Label'],
        showarrow=False,
        yshift=-50,
        font=dict(size=22, color='#333333', family="Arial, sans-serif"),
        xanchor='center'
    )

# Configure axes for bar chart
xa2 = common_xaxis.copy()
xa2['title'] = dict(text="Terrain Type", font=axis_font)

ya2 = common_yaxis.copy()
ya2['title'] = dict(text="Harmonic Mean Performance", font=axis_font)
ya2['range'] = [0, best_hm['HM_num'].max() * 1.15]

fig2.update_layout(
    title=dict(text="<b>B</b>  Optimal performance by terrain", font=title_font, x=0.02),
    xaxis=xa2,
    yaxis=ya2,
    width=1100,
    height=1000,
    showlegend=False,
    **publication_layout
)

fig2.write_html('Figure2_Optimal_Performance.html')
try:
    fig2.write_image('Figure2_Optimal_Performance.png', scale=3)
    fig2.write_image('Figure2_Optimal_Performance.pdf')
except Exception as e:
    print(f"Image export requires kaleido: {e}")

# =========================================================
# PLOT 3: Top-5 Configurations Table for Each Terrain
# =========================================================
fig3 = go.Figure()

# Prepare data for each environment
df_valid = df_all.dropna(subset=['HM_num'])
y_position = 0
row_height = 1
section_gap = 2

all_cells_env = []
all_cells_rank = []
all_cells_param = []
all_cells_lag = []
all_cells_hm = []
all_cells_vel = []
all_cells_cot = []

for env_idx, env in enumerate(['Ground', 'Slope', 'Water']):
    env_data = df_valid[df_valid['Environment'] == env].copy()
    top5 = env_data.nlargest(5, 'HM_num').reset_index(drop=True)

    for rank, row in top5.iterrows():
        # Create configuration string
        if env == 'Slope':
            config_str = f"Slope: {row['Config_Param']}"
        else:
            config_str = f"Amp: {row['Config_Param']}"

        all_cells_env.append(env)
        all_cells_rank.append(f"#{rank + 1}")
        all_cells_param.append(config_str)
        all_cells_lag.append(f"Lag: {row['Lag']}")
        all_cells_hm.append(f"{row['HM_num']:.2f}")
        all_cells_vel.append(f"{row['Vel_num']:.1f}")
        all_cells_cot.append(f"{row['CoT_num']:.2f}")

# Create table
fig3 = go.Figure(data=[go.Table(
    columnwidth=[100, 60, 120, 80, 100, 100, 100],
    header=dict(
        values=['<b>Terrain</b>', '<b>Rank</b>', '<b>Configuration</b>', '<b>Lag</b>',
                '<b>HM Score</b>', '<b>Vel (cm/s)</b>', '<b>CoT</b>'],
        fill_color='#4a4a4a',
        font=dict(color='white', size=28, family="Arial, sans-serif"),
        align='center',
        height=50,
        line=dict(color='#000000', width=2)
    ),
    cells=dict(
        values=[all_cells_env, all_cells_rank, all_cells_param, all_cells_lag,
                all_cells_hm, all_cells_vel, all_cells_cot],
        fill_color=[['#d6e9f7' if env == 'Ground' else '#ffe5cc' if env == 'Slope' else '#d5f4d5'
                     for env in all_cells_env]],
        font=dict(color='#000000', size=26, family="Arial, sans-serif"),
        align=['center', 'center', 'left', 'center', 'center', 'center', 'center'],
        height=45,
        line=dict(color='#666666', width=1.5)
    )
)])

fig3.update_layout(
    title=dict(text="<b>C</b>  Top-5 configurations by terrain type",
               font=title_font, x=0.02),
    width=1600,
    height=1000,
    margin=dict(l=40, r=40, t=100, b=40),
    paper_bgcolor='white'
)

fig3.write_html('Figure3_Top5_Configurations.html')
try:
    fig3.write_image('Figure3_Top5_Configurations.png', scale=3)
    fig3.write_image('Figure3_Top5_Configurations.pdf')
except Exception as e:
    print(f"Image export requires kaleido: {e}")

# =========================================================
# SUMMARY REPORT
# =========================================================
print("\n" + "=" * 70)
print("PUBLICATION-READY FIGURES GENERATED")
print("=" * 70)
print("\nOutputs:")
print("  • Figure1_Performance_Landscape.html/png/pdf")
print("  • Figure2_Optimal_Performance.html/png/pdf")
print("  • Figure3_Top5_Configurations.html/png/pdf")
print("\nKey improvements implemented:")
print("  ✓ Increased font sizes (Title: 36pt, Axis: 30pt, Ticks: 26pt)")
print("  ✓ Legend moved to top-right corner")
print("  ✓ Filtered out Ground outliers with CoT > 12")
print("  ✓ Top-5 performers highlighted with stars and darker colors")
print("  ✓ New table showing top-5 configurations for each terrain")
print("  ✓ Colorblind-safe palette with terrain-specific highlighting")
print("  ✓ Vector PDF output for scalability")
print("  ✓ 3x DPI scaling for crisp raster images")
print("=" * 70)

# Print top-5 summary to console
print("\n" + "=" * 70)
print("TOP-5 CONFIGURATIONS BY TERRAIN")
print("=" * 70)
for env in ['Ground', 'Slope', 'Water']:
    env_data = df_valid[df_valid['Environment'] == env].copy()
    top5 = env_data.nlargest(5, 'HM_num').reset_index(drop=True)
    print(f"\n{env.upper()}:")
    for rank, row in top5.iterrows():
        config = f"{row['Config_Param']} {row['Param_Name'].lower()}"
        print(
            f"  #{rank + 1}: {config}, Lag {row['Lag']} | HM={row['HM_num']:.2f}, Vel={row['Vel_num']:.1f}, CoT={row['CoT_num']:.2f}")
print("=" * 70)