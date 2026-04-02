import pandas as pd
import numpy as np
import plotly.graph_objects as go

# --- 1. Load Data ---
path_sim = r'F:\PREMALab\Mass-Shift\Code\Python\Simulated_Summary_Extended2.csv'


def load_clean_data(filepath):
    df = pd.read_csv(filepath)
    for col in ['Lag', 'Vel (cm/s)']:
        if col in df.columns and df[col].dtype == object:
            df[col] = df[col].str.replace(',', '.').astype(float)
    return df


df_sim = load_clean_data(path_sim)

# --- 2. Sorting: Reversed (Head-Heavy at Top, Tail-Heavy at Bottom) ---
water_labels = sorted(
    df_sim['Water (H, T)'].unique(),
    key=lambda x: int(x.strip('()').split(',')[0]),
    reverse=True
)

# --- 3. Grid Spacing & Color Baselines ---
global_vmin = df_sim['Vel (cm/s)'].quantile(0.02)
global_vmax = df_sim['Vel (cm/s)'].quantile(0.98)

unique_x = np.sort(df_sim['Amplitude'].unique())
unique_y = np.sort(df_sim['Lag'].unique())
dx = unique_x[1] - unique_x[0] if len(unique_x) > 1 else 1
dy = unique_y[1] - unique_y[0] if len(unique_y) > 1 else 1

border_gap = 0.15
x_radius = (dx / 2.0) * (1.0 - border_gap)
y_radius = (dy / 2.0) * (1.0 - border_gap)

fig = go.Figure()

# --- 4. Build the 3D Stack using Mesh3d ---
for depth_idx, wp in enumerate(water_labels):
    sub_sim = df_sim[df_sim['Water (H, T)'] == wp]

    Z_values = sub_sim.pivot(index='Lag', columns='Amplitude', values='Vel (cm/s)')
    x_coords = Z_values.columns.values
    y_coords = Z_values.index.values
    height_val = (len(water_labels) - depth_idx) * 4

    x_verts, y_verts, z_verts = [], [], []
    i_faces, j_faces, k_faces = [], [], []
    intensities = []

    hov_x, hov_y, hov_z, hov_text = [], [], [], []
    v_idx = 0

    for y_val in y_coords:
        for x_val in x_coords:
            vel = Z_values.loc[y_val, x_val]
            if np.isnan(vel):
                continue

            x_verts.extend([x_val - x_radius, x_val + x_radius, x_val + x_radius, x_val - x_radius])
            y_verts.extend([y_val - y_radius, y_val - y_radius, y_val + y_radius, y_val + y_radius])
            z_verts.extend([height_val] * 4)

            i_faces.extend([v_idx, v_idx])
            j_faces.extend([v_idx + 1, v_idx + 2])
            k_faces.extend([v_idx + 2, v_idx + 3])

            intensities.extend([vel, vel])
            v_idx += 4

            hov_x.append(x_val)
            hov_y.append(y_val)
            hov_z.append(height_val)
            hov_text.append(f"Water: {wp}<br>Amp: {x_val}<br>Lag: {y_val}<br>Vel: {vel:.2f}")

    fig.add_trace(go.Mesh3d(
        x=x_verts, y=y_verts, z=z_verts,
        i=i_faces, j=j_faces, k=k_faces,
        intensity=intensities,
        intensitymode='cell',
        colorscale='Turbo',
        cmin=global_vmin,
        cmax=global_vmax,
        showscale=(depth_idx == 0),
        # --- Enlarged Colorbar Fonts ---
        colorbar=dict(
            title="Vel (cm/s)",
            title_font=dict(size=24),
            tickfont=dict(size=20),
            x=1.0,  # Pushed right to make room for big fonts
            thickness=20
        ),
        flatshading=True,
        hoverinfo='skip',
        name=wp
    ))

    fig.add_trace(go.Scatter3d(
        x=hov_x, y=hov_y, z=hov_z,
        mode='markers',
        marker=dict(size=1, color='rgba(0,0,0,0)'),
        text=hov_text,
        hovertemplate="%{text}<extra></extra>",
        showlegend=False
    ))

# --- 5. Formatting ---
fig.update_layout(
    title=dict(
        text='3D Stacked Blocky Performance Map',
        font=dict(size=48)
    ),
    scene=dict(
        xaxis=dict(
            # Using <br> to push the title outward
            title=dict(text='<br>Amplitude', font=dict(size=28)),
            tickfont=dict(size=16),
            showbackground=False
        ),
        yaxis=dict(
            # Using <br> to push the title outward
            title=dict(text='<br>Lag (rad)', font=dict(size=28)),
            tickfont=dict(size=16),
            showbackground=False
        ),
        zaxis=dict(
            # Adding <br> spaces pushes the Z-axis title away from the massive text
            title=dict(text=' ', font=dict(size=28)),
            tickfont=dict(size=16),
            tickmode='array',
            tickvals=[(len(water_labels) - i) * 4 for i in range(len(water_labels))],
            ticktext=water_labels,
            showbackground=False
        ),
        camera=dict(eye=dict(x=1.8, y=1.8, z=1.5))
    ),
    width=1400,
    height=1200,
    template="plotly_white",
    margin=dict(l=50, r=150, b=50, t=100)
)

# Save
output_path = r'F:\PREMALab\Mass-Shift\Experiments\Figures\Sim_3D_Blocky_Final_V5.html'
fig.write_html(output_path)
print(f"Success! Corrected discrete 3D blocky stack saved to: {output_path}")