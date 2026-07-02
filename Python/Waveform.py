import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots


# --- 1. KINEMATICS & PHYSICS ENGINE ---
def get_robot_state(water_location, phase=0.0, lag=1.2, amp_deg=70.0):
    """
    Replicates the PyQt5 physics to get the X, Y coordinates and CoM
    of the stable robot posture.
    """
    LENGTHS = [100.0, 80.0, 125.0, 80.0, 100.0]
    BASE_MASSES = [63.0, 260.0, 130.0, 280.0, 63.0]

    # Distribute water mass (300g total)
    masses = list(BASE_MASSES)
    if water_location == 'tail':
        masses[0] += 300.0
    elif water_location == 'mid':
        masses[0] += 150.0
        masses[4] += 150.0
    elif water_location == 'head':
        masses[4] += 300.0

    amp_rad = np.radians(amp_deg)

    # Calculate angles
    joint_angles = np.zeros(4)
    for i in range(4):
        wave = np.sin(phase + i * lag) * amp_rad
        lift = max(0.0, wave)
        joint_angles[i] = lift * -1.0  # LIFT_SIDE from sim

    angles = np.zeros(5)
    for i in range(4):
        angles[i + 1] = angles[i] + joint_angles[i]

    # Node coordinates
    loc_x = np.zeros(6)
    loc_y = np.zeros(6)
    for i in range(5):
        loc_x[i + 1] = loc_x[i] + LENGTHS[i] * np.cos(angles[i])
        loc_y[i + 1] = loc_y[i] + LENGTHS[i] * np.sin(angles[i])

    # Center of Mass Calculation
    total_mass = sum(masses)
    local_com_x = sum(masses[i] * (loc_x[i] + loc_x[i + 1]) / 2.0 for i in range(5)) / total_mass
    local_com_y = sum(masses[i] * (loc_y[i] + loc_y[i + 1]) / 2.0 for i in range(5)) / total_mass

    # Gravity Drop Physics (Finding stable resting orientation)
    best_joints_x, best_joints_y = loc_x, loc_y
    min_energy = float('inf')
    final_com_x, final_com_y = local_com_x, local_com_y

    for i in range(6):
        for j in range(i + 1, 6):
            dx = loc_x[j] - loc_x[i]
            dy = loc_y[j] - loc_y[i]
            if np.hypot(dx, dy) < 1e-5: continue

            angle = np.arctan2(dy, dx)
            cos_a, sin_a = np.cos(-angle), np.sin(-angle)

            rot_x = loc_x * cos_a - loc_y * sin_a
            rot_y = loc_x * sin_a + loc_y * cos_a

            shift_y = np.min(rot_y)
            rot_y -= shift_y

            if rot_y[i] < 1e-3 and rot_y[j] < 1e-3:
                com_x_rot = local_com_x * cos_a - local_com_y * sin_a
                com_y_rot = local_com_x * sin_a + local_com_y * cos_a - shift_y

                contact_xs = [rot_x[k] for k in range(6) if rot_y[k] < 1e-3]
                min_cx, max_cx = min(contact_xs), max(contact_xs)
                is_stable = (min_cx - 5.0) <= com_x_rot <= (max_cx + 5.0)

                score = com_y_rot + (0 if is_stable else 10000.0)
                if score < min_energy:
                    min_energy = score
                    best_joints_x, best_joints_y = rot_x, rot_y
                    final_com_x, final_com_y = com_x_rot, com_y_rot

    # Shift robot so the first node starts at X=0
    offset = best_joints_x[0]
    return best_joints_x - offset, best_joints_y, final_com_x - offset, final_com_y


# --- 2. DATA GENERATION ---
# Get Robot States (Phase = 0 to capture a snapshot of the wave effect)
tx_head, ty_head, com_x_head, com_y_head = get_robot_state('head')
tx_mid, ty_mid, com_x_mid, com_y_mid = get_robot_state('mid')
tx_tail, ty_tail, com_x_tail, com_y_tail = get_robot_state('tail')

# Generate Sinusoidal Signal Data
time_steps = np.linspace(0, 4 * np.pi, 200)
signals = []
for i in range(4):
    wave = np.sin(time_steps + i * 1.2) * 70.0
    lift_signal = np.maximum(0.0, wave)  # The robot's rectified lifting logic
    signals.append(lift_signal)

# --- 3. LIQUID GLASS DESIGN SYSTEM ---
COLORS = {
    'sky': 'rgba(56, 189, 248, 0.95)',
    'magenta': 'rgba(236, 72, 153, 0.95)',
    'orange': 'rgba(251, 146, 60, 0.95)',
    'green': 'rgba(34, 197, 94, 0.95)',
    'slate': '#1e293b',
    'grid': '#cbd5e1'
}

FROSTED_BORDER = dict(color='white', width=4)


def glass_marker(color):
    return dict(size=22, color=color, line=FROSTED_BORDER)


def add_robot_trace(fig, x, y, com_x, com_y, color, name, row, col):
    # Links & Nodes
    fig.add_trace(go.Scatter(
        x=x, y=y, mode='lines+markers', name=f'{name} Nodes',
        line=dict(color=color, width=8),
        marker=glass_marker(color),
        showlegend=False
    ), row=row, col=col)

    # Center of Mass
    fig.add_trace(go.Scatter(
        x=[com_x], y=[com_y], mode='markers', name=f'{name} CoM',
        marker=dict(size=30, symbol='star', color=COLORS['green'], line=FROSTED_BORDER),
        showlegend=False
    ), row=row, col=col)


# --- 4. PLOT ASSEMBLY ---
fig = make_subplots(
    rows=2, cols=2,
    subplot_titles=(
        "<b>1. Joint Control Signals (Rectified Sine)</b>",
        "<b>2. Posture: Water in Head (Sky Blue)</b>",
        "<b>3. Posture: Water in Mid (Magenta)</b>",
        "<b>4. Posture: Water in Tail (Orange)</b>"
    )
)

# Plot 1: Signals
colors_signal = [COLORS['sky'], COLORS['magenta'], COLORS['orange'], COLORS['slate']]
for i in range(4):
    fig.add_trace(go.Scatter(
        x=time_steps, y=signals[i], mode='lines', name=f'Joint {i + 1}',
        line=dict(color=colors_signal[i], width=5)
    ), row=1, col=1)

# Plots 2, 3, 4: Robot States
add_robot_trace(fig, tx_head, ty_head, com_x_head, com_y_head, COLORS['sky'], "Head", 1, 2)
add_robot_trace(fig, tx_mid, ty_mid, com_x_mid, com_y_mid, COLORS['magenta'], "Mid", 2, 1)
add_robot_trace(fig, tx_tail, ty_tail, com_x_tail, com_y_tail, COLORS['orange'], "Tail", 2, 2)

# --- 5. STYLING OVERRIDES ---
fig.update_layout(
    title=dict(
        text="<b>Worm Robot Locomotion: Mass Distribution vs. Shape</b>",
        font=dict(family="Arial, sans-serif", size=48, color=COLORS['slate']),
        x=0.5, xanchor='center'
    ),
    font=dict(family="Arial, sans-serif", color=COLORS['slate']),
    paper_bgcolor='white',
    plot_bgcolor='white',
    margin=dict(l=40, r=40, t=120, b=80),
    legend=dict(
        orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5,
        bgcolor='white', bordercolor=COLORS['grid'], borderwidth=4,
        font=dict(size=16)
    )
)

# Apply strict gridline and axis styles across all subplots
for i in range(1, 3):
    for j in range(1, 3):
        fig.update_xaxes(
            showgrid=True, gridcolor=COLORS['grid'], gridwidth=2,
            zeroline=True, zerolinecolor=COLORS['grid'], zerolinewidth=3,
            row=i, col=j
        )
        fig.update_yaxes(
            showgrid=True, gridcolor=COLORS['grid'], gridwidth=2,
            zeroline=True, zerolinecolor=COLORS['grid'], zerolinewidth=3,
            row=i, col=j
        )

        # Lock scales for the robot plots so differences are visually accurate
        if not (i == 1 and j == 1):
            fig.update_xaxes(range=[-50, 400], row=i, col=j)
            fig.update_yaxes(range=[-20, 200], row=i, col=j)

# Update subplot title fonts to match the slate requirement
for annotation in fig['layout']['annotations']:
    annotation['font'] = dict(size=20, color=COLORS['slate'])

# Render
fig.show()