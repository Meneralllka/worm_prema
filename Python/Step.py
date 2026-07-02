import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np

# =====================================================================
# 1. DATA PARAMETERS
# =====================================================================

max_time = 14.0
times = np.linspace(0, max_time, 100)

# Water is entirely in the Head (y=1 represents Head, y=0 represents Tail)
water_placement_data = np.ones_like(times)

# Robot height stays 0 cm, but we will scale the Y-axis to 4 cm
robot_height_data = np.zeros_like(times)


# =====================================================================


def build_timeline_figure():
    # Create subplots with a shared X-axis
    fig = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.15
    )

    # --- Top Plot: Water Placement ---
    fig.add_trace(
        go.Scatter(
            x=times, y=water_placement_data,
            mode="lines", line=dict(color="#1f8cd5", width=58),  # Scaled width
            showlegend=False
        ),
        row=1, col=1
    )

    # --- Bottom Plot: Robot Height ---
    fig.add_trace(
        go.Scatter(
            x=times, y=robot_height_data,
            mode="lines", line=dict(color="#1f8cd5", width=58),  # Scaled width
            showlegend=False
        ),
        row=2, col=1
    )

    # --- Layout and Styling ---
    # Global Font Application (Arial) and Dimensions
    fig.update_layout(
        font=dict(family="Arial, sans-serif", color="black"),
        plot_bgcolor="white",
        paper_bgcolor="white",
        width=23000,
        height=6900,
        margin=dict(l=3450, r=1150, t=920, b=1380),  # Scaled margins
    )

    # Style X-Axes
    fig.update_xaxes(
        showgrid=False, zeroline=False,
        showline=True, linewidth=35, linecolor="black",
        ticks="outside", tickwidth=35, ticklen=100,  # Scaled ticks
        range=[0, max_time + 0.5],
        row=1, col=1
    )
    fig.update_xaxes(
        title_text="Time [s]", title_font=dict(size=368, family="Arial, sans-serif", color="black"),  # Scaled font
        showgrid=False, zeroline=False,
        showline=True, linewidth=35, linecolor="black",
        ticks="outside", tickwidth=35, ticklen=100,
        tickvals=[0, max_time], ticktext=["0", f"{int(max_time)} s"],
        tickfont=dict(size=322, family="Arial, sans-serif", color="black"),  # Scaled font
        range=[0, max_time + 0.5],
        row=2, col=1
    )

    # Style Y-Axes
    fig.update_yaxes(
        title_text="Water<br>placement", title_font=dict(size=368, family="Arial, sans-serif", color="black"),
        tickvals=[0, 1], ticktext=["Tail", "Head"],
        tickfont=dict(size=322, family="Arial, sans-serif", color="black"),
        showgrid=False, zeroline=False,
        showline=True, linewidth=35, linecolor="black",
        ticks="outside", tickwidth=35, ticklen=100,
        range=[-0.2, 1.2],
        row=1, col=1
    )

    fig.update_yaxes(
        title_text="Robot<br>height [cm]", title_font=dict(size=368, family="Arial, sans-serif", color="black"),
        tickvals=[0, 4], ticktext=["0", "4"],
        tickfont=dict(size=322, family="Arial, sans-serif", color="black"),
        showgrid=False, zeroline=False,
        showline=True, linewidth=35, linecolor="black",
        ticks="outside", tickwidth=35, ticklen=100,
        range=[-0.5, 4.5],
        row=2, col=1
    )

    # Scaled Arrows
    for row_idx in [1, 2]:
        x_ref = "x domain" if row_idx == 1 else f"x{row_idx} domain"
        y_ref = "y domain" if row_idx == 1 else f"y{row_idx} domain"

        fig.add_annotation(
            x=1.0, y=0, xref=x_ref, yref=y_ref,
            ax=-230, ay=0, showarrow=True, arrowhead=2, arrowsize=1, arrowwidth=35,  # Scaled arrow dims
        )

    return fig


if __name__ == "__main__":
    fig = build_timeline_figure()

    # Export the figure to SVG
    output_filename = "timeline_plot_23k.svg"
    fig.write_image(output_filename)
    print(f"Plot saved successfully to {output_filename}")