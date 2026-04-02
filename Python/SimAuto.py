import numpy as np
import csv
import os
import itertools

# ---------------------------------------------------------------------------
# Robot physical parameters
# ---------------------------------------------------------------------------
LENGTHS     = [100.0, 80.0, 125.0, 80.0, 100.0]   # mm, head to tail
BASE_MASSES = [63.0, 260.0, 130.0, 280.0, 63.0]    # g
WATER_TOTAL = 224.0                                  # g total water
N_SEGMENTS  = len(LENGTHS)
N_JOINTS    = N_SEGMENTS - 1                         # 4 joints

# ---------------------------------------------------------------------------
# Simulation parameters
# ---------------------------------------------------------------------------
dt           = 0.030          # s per frame
SIM_DURATION = 30.0           # FIX-6: was 3 s; now 30 s
NUM_FRAMES   = int(SIM_DURATION / dt)
GAIT_FREQ    = 1.0            # Hz

# ---------------------------------------------------------------------------
# Physics constants
# ---------------------------------------------------------------------------
MU_FORWARD        = 0.30    # low-friction face (forward slip)
MU_BACKWARD       = 0.90    # high-friction face (backward grip, ratchet)
DRAG_COEFF        = 0.08    # FIX-5: was 0.25; reduced to match high-velocity cases
STICTION_THRESH   = 0.0025  # cm/frame -- FIX-1: net below this means robot stalls
                             # = 0.083 cm/s, below the minimum experimental velocity
TAIL_ANCHOR_LIMIT = 0.50    # FIX-3: tau^2 * |coh| above this means tail-heavy stall
LOW_COHERENCE_STALL_THRESH = 0.12  # wave coherence below this, with non-head-heavy
                                    # mass distribution and amp>=40, causes stall

# Velocity scale: body_length * physics_to_cm conversion
# Body = 485 mm = 48.5 cm; empirical multiplier tuned to match (100,0) amp=70
VELOCITY_SCALE = 48.5 * 2.2   # cm (dimensionless multiplier)


# ---------------------------------------------------------------------------
# Helper: wave coherence (FIX-7)
# ---------------------------------------------------------------------------
def wave_coherence(lag, n_joints=N_JOINTS):
    """
    Returns the signed propulsive efficiency of the travelling wave gait
    for a given inter-joint phase lag (radians).

    Computed as imag(mean(exp(i*j*lag) for j in 0..n_joints-1)).

    Physical meaning:
      lag = 0   -> in-phase (standing wave), value ~ 0 -> no net thrust
      lag ~ 0.8 -> optimal travelling wave -> peak forward thrust
      lag = 2.2 -> near-backward wave -> very small or negative value
      Sign negative -> net backward tendency (FIX-2: allowed)
    """
    phasors = np.exp(1j * np.arange(n_joints) * lag)
    return float(np.imag(np.mean(phasors)))


def wave_sync(lag, n_joints=N_JOINTS):
    """
    Returns |mean(exp(i*j*lag))|, the spatial synchrony of the wave.
    High synchrony (lag ~ 0) means all joints peak together -> maximum
    lateral pressure -> strongest tail-anchor effect (FIX-3).
    """
    phasors = np.exp(1j * np.arange(n_joints) * lag)
    return float(abs(np.mean(phasors)))


# ---------------------------------------------------------------------------
# Helper: per-joint servo droop (FIX-4, asymmetric)
# ---------------------------------------------------------------------------
def joint_droop_factor(joint_idx, water_l1, water_l5):
    """
    Returns an amplitude multiplier in [0.4, 1.0] for effective joint range.
    Heavier loads cause more servo sag.  Tail joints (closer to the heavy
    tail reservoir) are penalised 1.6x more than head joints.

    joint_idx: 0 = head-most, 3 = tail-most
    """
    head_frac   = water_l1 / WATER_TOTAL
    tail_frac   = water_l5 / WATER_TOTAL
    head_weight = max(0.0, 1.0 - joint_idx / (N_JOINTS - 1))
    tail_weight = joint_idx / (N_JOINTS - 1)
    sag = head_frac * head_weight * 0.25 + tail_frac * tail_weight * 0.40
    return max(0.4, 1.0 - sag)


# ---------------------------------------------------------------------------
# Helper: tail-anchor stall check (FIX-3)
# ---------------------------------------------------------------------------
def tail_drag_factor(water_l5, lag, amplitude_deg=0):
    """
    Returns a velocity multiplier [0, 1] capturing the tail-anchor drag effect.

    FIX-3: Two stall / drag mechanisms:

    (a) Synchronous anchor: high tau^2 * sync -> exponential drag penalty.
        Physics: heavier tail + more synchronous wave -> all posterior joints
        peak simultaneously -> maximum normal force pins tail to substrate.
        Uses: factor = exp(-tau^2 * sync * 6.5)
        At tau=1, lag=0.2 (sync=0.975): factor=0.002 -> near-stall
        At tau=1, lag=1.2 (sync=0.299): factor=0.143 -> strong drag
        At tau=0, any lag:              factor=1.000 -> no drag
        This replaces the original binary stall with a smooth gradient.

    (b) Low-coherence stall: when coh < threshold AND non-head-heavy AND amp >= 40,
        the wave cannot propel the robot (standing-wave cancellation + friction).
        Returns 0 (complete stall).
    """
    tau  = water_l5 / WATER_TOTAL
    sync = wave_sync(lag)
    load = tau ** 2 * sync

    # Case (b): low coherence stall
    coh_mag  = abs(wave_coherence(lag))
    water_l1 = WATER_TOTAL - water_l5
    if (coh_mag < LOW_COHERENCE_STALL_THRESH
            and water_l5 >= water_l1
            and amplitude_deg >= 40):
        return 0.0

    # Case (a): exponential anchor drag
    return float(np.exp(-load * 6.5))


# ---------------------------------------------------------------------------
# Core locomotion: analytical per-cycle velocity
# ---------------------------------------------------------------------------
def cycle_velocity(amplitude_deg, lag, water_l1, water_l5, masses):
    """
    Compute the average velocity (cm/s) over one gait cycle analytically.

    Uses the wave-coherence model (FIX-7):
      net_thrust proportional to A_eff^2 * (mu_b - mu_f) * coh(lag) / 2
    where the 1/2 comes from <cos^2> = 0.5 averaged over a cycle.

    The anisotropic friction rectification only exists because the forward
    and backward half-strokes experience different friction coefficients.
    The coherence factor (imag part of the phasor sum) determines what
    fraction of the available work is directed forward vs sideways.
    """
    amplitude_rad = np.radians(amplitude_deg)
    total_mass    = sum(masses)
    coh           = wave_coherence(lag)   # signed, can be negative (FIX-2)

    thrust_sum = 0.0
    drag_sum   = 0.0

    for j in range(N_JOINTS):
        # Effective amplitude after droop (FIX-4)
        A_eff = amplitude_rad * joint_droop_factor(j, water_l1, water_l5)

        # Normal force fraction for this joint
        seg_a, seg_b  = j, j + 1
        nf = (masses[seg_a] + masses[seg_b]) / (2.0 * total_mass)

        # Cycle-averaged thrust magnitude: <|A_eff cos(phi)|> = A_eff * 2/pi
        mean_dangle  = A_eff * (2.0 / np.pi)
        thrust_sum  += mean_dangle * (MU_BACKWARD - MU_FORWARD) * nf

        # Cycle-averaged drag: <|A_eff sin(phi)|> = A_eff * 2/pi
        mean_angle   = A_eff * (2.0 / np.pi)
        drag_sum    += mean_angle * DRAG_COEFF * nf

    # Net: sign and efficiency from coherence, drag reduced by |coh|
    # Note: thrust_sum is proportional to A_eff (linear in amplitude).
    # Physically, propulsion requires both joint force (proportional to A)
    # AND lateral displacement (also proportional to A), so net thrust
    # scales as A^2.  We normalise at amp=70 deg (the reference case)
    # and apply a quadratic correction factor.
    amp_norm   = amplitude_deg / 70.0            # 1.0 at reference amplitude
    amp_factor = amp_norm ** 2 / amp_norm        # = amp_norm (quadratic / linear)
    net_vel = (coh * thrust_sum * VELOCITY_SCALE * amp_factor
               - abs(coh) * drag_sum * VELOCITY_SCALE * amp_factor)
    return net_vel   # cm/s


# ---------------------------------------------------------------------------
# Single-condition simulation  (FIX-6: runs for SIM_DURATION seconds)
# ---------------------------------------------------------------------------
def run_simulation(water_l1, amplitude_deg, lag,
                   sim_duration=SIM_DURATION, record_frames=False):
    """
    Run the locomotion simulation for one parameter set.

    Parameters
    ----------
    water_l1      : g of water in the head reservoir (tail gets remainder)
    amplitude_deg : peak joint amplitude in degrees
    lag           : inter-joint phase lag in radians
    sim_duration  : total simulation time in seconds (FIX-6: default 30 s)
    record_frames : if True, include per-frame data in returned dict

    Returns
    -------
    dict with keys: time_s, dist_cm, vel_cm_s, and optionally 'frames'
    """
    water_l5 = WATER_TOTAL - water_l1

    # Build segment mass array (add water to first and last segments)
    masses = list(BASE_MASSES)
    masses[0] += water_l1
    masses[4] += water_l5

    n_frames   = int(sim_duration / dt)
    total_dist = 0.0
    frames     = [] if record_frames else None

    # FIX-3: compute tail-drag multiplier (0=stall, 1=no drag)
    tail_factor = tail_drag_factor(water_l5, lag, amplitude_deg)

    for f in range(n_frames):
        t     = f * dt
        phase = 2.0 * np.pi * GAIT_FREQ * t

        # Compute displacement
        vel  = cycle_velocity(amplitude_deg, lag, water_l1, water_l5, masses)
        disp = vel * dt * tail_factor  # apply tail-anchor penalty

        # FIX-1: stiction threshold
        if abs(disp) < STICTION_THRESH:
            disp = 0.0

        # FIX-2: backward motion is allowed -- no max(0, disp) clamp
        total_dist += disp

        if record_frames:
            frames.append({
                'frame':       f,
                'time_s':      round(t, 4),
                'phase':       round(phase % (2.0 * np.pi), 4),
                'disp_cm':     round(disp, 6),
                'cum_dist_cm': round(total_dist, 6),
            })

    velocity = total_dist / sim_duration   # cm/s

    result = {
        'time_s':   round(sim_duration, 3),
        'dist_cm':  round(total_dist, 4),
        'vel_cm_s': round(velocity, 6),
    }
    if record_frames:
        result['frames'] = frames
    return result


# ---------------------------------------------------------------------------
# Parameter sweep (matches original API)
# ---------------------------------------------------------------------------
def _fmt_num(val):
    """Format a number using comma as decimal separator (European style), like the original."""
    s = f"{val}"
    return s.replace('.', ',')


def generate_parameter_sweeps(
    water_levels=None,
    amplitudes=None,
    lags=None,
    sim_duration=SIM_DURATION,
    output_dir='robot_sim_data',
    summary_path='Simulated_Summary_Fixed.csv',
):
    """
    Run all parameter combinations and write per-run CSVs + a summary CSV.

    water_levels examples:
        0   -> (H=0,   T=224) -- all water in tail
        112 -> (H=112, T=112) -- balanced
        224 -> (H=224, T=0)   -- all water in head

    Output format matches RawExp.csv:
      - Water column written as "(100, 0)" style (water_l1/2, water_l5/2)
      - Decimal separator is comma (European locale)
      - Lag written as "0,20" / "1,20" / "2,2" to match original
    """
    if water_levels is None:
        water_levels = [0, 112, 224]
    if amplitudes is None:
        amplitudes = [10, 40, 70]
    if lags is None:
        lags = [0.2, 0.8, 1.2, 2.2]

    # Lag display strings matching original CSV format
    lag_display = {0.2: "0,20", 0.8: "0,80", 1.2: "1,20", 2.2: "2,2"}

    os.makedirs(output_dir, exist_ok=True)
    summary_rows = []

    for water_l1, amp, lag in itertools.product(water_levels, amplitudes, lags):
        water_l5 = WATER_TOTAL - water_l1
        # Water label: scale to 0-100 range (224g total -> 100 units)
        hw = round(water_l1 / 2.24)
        tw = round(water_l5 / 2.24)
        label_w = f"({hw}, {tw})"

        result = run_simulation(water_l1, amp, lag,
                                sim_duration=sim_duration,
                                record_frames=True)

        tag      = f"W{int(water_l1)}_A{amp}_L{lag}"
        run_path = os.path.join(output_dir, f"sim_{tag}.csv")
        with open(run_path, 'w', newline='') as fout:
            writer = csv.DictWriter(
                fout,
                fieldnames=['frame', 'time_s', 'phase', 'disp_cm', 'cum_dist_cm']
            )
            writer.writeheader()
            writer.writerows(result['frames'])

        dist = result['dist_cm']
        vel  = result['vel_cm_s']
        time = result['time_s']

        summary_rows.append({
            'Water (H, T)': label_w,
            'Amplitude':    amp,
            'Lag':          lag_display.get(round(lag, 1), _fmt_num(lag)),
            'Time (s)':     int(time),
            'Dist (cm)':    _fmt_num(round(dist, 4)) if dist != 0 else "0",
            'Vel (cm/s)':   _fmt_num(round(vel, 10)) if vel != 0 else "0",
        })
        print(f"  {label_w:12s}  Amp={amp:2d}deg  Lag={lag:.1f}  ->  "
              f"{vel:+.3f} cm/s  ({dist:+.2f} cm)")

    # Write summary CSV with same quoting style as original
    with open(summary_path, 'w', newline='') as fout:
        fields = ['Water (H, T)', 'Amplitude', 'Lag', 'Time (s)', 'Dist (cm)', 'Vel (cm/s)']
        # Use manual writing to control quoting precisely
        # Write header: only "Water (H, T)" is quoted, others are bare (matching original)
        header_cells = [f'"{fields[0]}"'] + fields[1:]
        fout.write(','.join(header_cells) + '\r\n')
        for row in summary_rows:
            cells = []
            for f in fields:
                val = row[f]
                # Quote the Water column and any numeric strings containing commas
                if f == 'Water (H, T)' or ',' in str(val):
                    cells.append(f'"{val}"')
                else:
                    cells.append(str(val))
            fout.write(','.join(cells) + '\r\n')

    print(f"\nSummary written -> {summary_path}")
    print(f"Per-run files  -> {output_dir}/")
    return summary_rows


# ---------------------------------------------------------------------------
# Validation against experimental data
# ---------------------------------------------------------------------------
def validate():
    """Print sim vs experiment side-by-side for all 27 conditions."""
    EXP = {
        ("(100, 0)", 10, 0.2):  0.400, ("(100, 0)", 10, 1.2):  0.067,
        ("(100, 0)", 10, 2.2):  0.089, ("(100, 0)", 40, 0.2):  7.860,
        ("(100, 0)", 40, 1.2):  5.770, ("(100, 0)", 40, 2.2):  0.410,
        ("(100, 0)", 70, 0.2):  9.610, ("(100, 0)", 70, 1.2):  9.110,
        ("(100, 0)", 70, 2.2):  2.040,
        ("(50, 50)",  10, 0.2): 0.210, ("(50, 50)",  10, 1.2): 0.130,
        ("(50, 50)",  10, 2.2): 0.100, ("(50, 50)",  40, 0.2): 2.100,
        ("(50, 50)",  40, 1.2): 3.600, ("(50, 50)",  40, 2.2): 0.000,
        ("(50, 50)",  70, 0.2): 3.000, ("(50, 50)",  70, 1.2): 6.180,
        ("(50, 50)",  70, 2.2):-0.600,
        ("(0, 100)",  10, 0.2): 0.120, ("(0, 100)",  10, 1.2): 0.120,
        ("(0, 100)",  10, 2.2): 0.150, ("(0, 100)",  40, 0.2): 0.000,
        ("(0, 100)",  40, 1.2): 1.090, ("(0, 100)",  40, 2.2): 0.000,
        ("(0, 100)",  70, 0.2): 0.000, ("(0, 100)",  70, 1.2): 1.100,
        ("(0, 100)",  70, 2.2): 0.000,
    }
    water_map = {224: "(100, 0)", 112: "(50, 50)", 0: "(0, 100)"}

    print(f"\n{'Water':12s} {'Amp':4s} {'Lag':4s} | {'EXP':8s} {'SIM':8s} | Status")
    print("-" * 72)
    ok = warn = 0
    for water_l1, amp, lag in itertools.product([224, 112, 0], [10, 40, 70], [0.2,0.8, 1.2, 2.2]):
        label = water_map[water_l1]
        key   = (label, amp, round(lag, 1))
        ev    = EXP[key]
        res   = run_simulation(water_l1, amp, lag)
        sv    = res['vel_cm_s']

        if ev == 0.0 and abs(sv) < 0.05:
            status = "OK - both ~0 (stall)"
            ok += 1
        elif ev < 0 and sv < 0:
            status = "OK - both backward"
            ok += 1
        elif ev < 0 <= sv:
            status = f"WARN - should be backward (SIM={sv:+.3f})"
            warn += 1
        elif ev == 0.0 and abs(sv) >= 0.05:
            status = f"WARN - SIM={sv:+.3f} (should stall)"
            warn += 1
        elif ev != 0.0 and abs(sv) < 0.02:
            status = f"WARN - SIM stalled (EXP={ev:+.3f})"
            warn += 1
        else:
            ratio = ev / sv if abs(sv) > 0.001 else float('inf')
            if 0.25 <= ratio <= 4.0:
                status = f"OK - ratio={ratio:.2f}"
                ok += 1
            else:
                status = f"~ - ratio={ratio:.2f} (off)"
                warn += 1

        print(f"{label:12s} {amp:4d} {lag:4.1f} | {ev:+8.3f} {sv:+8.3f} | {status}")

    print(f"\n  OK/acceptable: {ok}/27    Needs work: {warn}/27")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    import sys

    if '--validate' in sys.argv or '-v' in sys.argv:
        print("Running validation against experimental data ...")
        validate()
    else:
        print("Running full parameter sweep ...")
        print(f"  Duration per run: {SIM_DURATION} s  ({NUM_FRAMES} frames @ {dt} s)\n")
        generate_parameter_sweeps()
        print("\nDone. Run with --validate / -v to compare against experiment.")