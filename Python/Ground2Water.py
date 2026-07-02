import pandas as pd
import plotly.graph_objects as go

# 1. Read the data
df = pd.read_csv('Results - Sheet1.csv')

# Clean up column names and string data to prevent trailing-space errors
df.columns = df.columns.str.strip()
df['Config'] = df['Config'].str.strip()
df['Phase Type'] = df['Phase Type'].str.strip()

# 2. Calculate the average (mean) and standard deviation (std) for error bars
grouped = df.groupby(['Config', 'Phase Type'])['Time (s)'].agg(['mean', 'std']).reset_index()

# 3. Extract the unique configs in the exact order they appear in the CSV
configs = df['Config'].drop_duplicates().tolist()

# Define phase order and visual colors
phases = ['Ground', 'Transfer', 'Water']
colors = {
    'Ground': '#8c564b',  # Brown
    'Transfer': '#ff7f0e',  # Orange
    'Water': '#1f77b4'  # Blue
}

fig = go.Figure()

# 4. Build the stacked bars
for phase in phases:
    # Filter data specific to this phase
    phase_data = grouped[grouped['Phase Type'] == phase]

    # Align the data to match the overarching 'configs' axis order
    phase_data = phase_data.set_index('Config').reindex(configs).reset_index()

    # Extract the calculations as explicit Python lists
    means = phase_data['mean'].fillna(0).tolist()
    stds = phase_data['std'].fillna(0).tolist()

    fig.add_trace(go.Bar(
        name=phase,
        x=configs,
        y=means,
        # Thickened and formatted explicitly for native lists
        error_y=dict(
            type='data',
            array=stds,
            symmetric=False,
            arrayminus=[0] * len(stds),  # Prevents overlap downwards
            visible=True,
            thickness=4,  # Increased thickness
            width=16,  # Increased width
            color='black'
        ),
        marker_color=colors.get(phase, '#000000'),
        marker_line_color='black',
        marker_line_width=1.5
    ))

# 5. Layout and Formatting (1080p Height, scaled proportionally)
fig.update_layout(
    barmode='stack',
    title=dict(text="Average Time per Phase by Configuration", font=dict(size=32)),
    xaxis_title=dict(text="Configuration", font=dict(size=24)),
    yaxis_title=dict(text="Average Time (s)", font=dict(size=24)),
    plot_bgcolor='white',
    paper_bgcolor='white',
    font=dict(family="Arial, sans-serif", color="black", size=20),
    width=1600,
    height=1080,  # 1080px resolution
    margin=dict(l=80, r=80, t=100, b=80),
    legend=dict(
        title=dict(text="Phase Type", font=dict(size=24)),
        bordercolor="black",
        borderwidth=1,
        x=1.02,
        y=1,
        font=dict(size=20)
    )
)

# Clean and style axes
fig.update_xaxes(
    showline=True, linewidth=2, linecolor='black',
    ticks='outside', mirror=True, tickfont=dict(size=20)
)
fig.update_yaxes(
    showline=True, linewidth=2, linecolor='black',
    ticks='outside', gridcolor='#e5e5e5', mirror=True, tickfont=dict(size=20)
)

# Export options
fig.write_image('stacked_barchart_1080_thick_errorbars.svg')
# fig.show() # Uncomment to view interactively
print("Plot successfully saved to stacked_barchart_1080_thick_errorbars.svg")