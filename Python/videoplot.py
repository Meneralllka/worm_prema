import plotly.graph_objects as go
import pandas as pd

# 1. Define the data points based on your sketch
# Red Line (Head Water): High -> Drops -> Low -> Rises -> High
time_red = [0, 30, 40, 75, 95, 100]
head_water = [10, 10, 0.2, .2, 10, 10]

# Blue Line (Tail Water): Low -> Rises -> High -> Drops -> Low
time_blue = [0, 30, 40, 75, 95, 100]
tail_water = [.2, .2, 10, 10, .2, .2]

# 2. Create the figure
fig = go.Figure()

# Add Head Water (Red)
fig.add_trace(go.Scatter(
    x=time_red, y=head_water,
    name='Head Water',
    line=dict(color='red', width=6),
    mode='lines'
))

# Add Tail Water (Blue)
fig.add_trace(go.Scatter(
    x=time_blue, y=tail_water,
    name='Tail Water',
    line=dict(color='blue', width=6),
    mode='lines'
))

# 3. Apply Styling
fig.update_layout(
    # Background and Canvas
    plot_bgcolor='white',
    paper_bgcolor='white',

    # Font and Labels
    font=dict(family="Arial", size=72, color="black"),
    xaxis_title="Time",
    yaxis_title="Water Level",

    # Axis styling (adding the L-shape axis lines)
    xaxis=dict(
        showline=True,
        linewidth=3,
        linecolor='black',
        mirror=False,
        ticks='outside',
        tickvals=[0, 40, 94, 100]  # Matching your specific labels
    ),
    yaxis=dict(
        showline=True,
        linewidth=3,
        linecolor='black',
        mirror=False,
        showticklabels=False  # Kept clean as per the sketch
    ),

    # Legend and Margins
    showlegend=True,
    margin=dict(l=50, r=50, t=50, b=50)
)

# 4. Show and Save
# Note: To save as PNG, you need the 'kaleido' package installed (pip install kaleido)
fig.write_image("water_levels_plot.png", width=1200, height=800, scale=2)
fig.show()