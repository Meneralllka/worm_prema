'''
import os
import glob
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots


def plot_csv_files_plotly(input_folder, output_folder):
    """
    Reads CSV files, processes offset/noise/energy, and outputs
    HTML, SVG Plotly charts, and a summary CSV of the energy totals.
    """
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    csv_files = glob.glob(os.path.join(input_folder, "*.csv"))

    if not csv_files:
        print(f"No CSV files found in {input_folder}")
        return

    # Initialize a list to hold the summary data
    summary_data = []

    for file_path in csv_files:
        # Ignore the summary file if it already exists in the directory
        if file_path.endswith('energy_summary.csv'):
            continue

        file_name = os.path.basename(file_path)
        print(f"Processing: {file_name}")

        try:
            df = pd.read_csv(file_path)

            required_cols = ['Timestamp_ms', 'Voltage_V', 'Current_A']
            if not all(col in df.columns for col in required_cols):
                print(f"Skipping {file_name}: Missing columns {required_cols}")
                continue

            # --- 0. TIME CONVERSION & OFFSET ---
            df['Time_s'] = df['Timestamp_ms'] / 1000.0
            df['Time_s'] = df['Time_s'] - df['Time_s'].iloc[0]

            dt = df['Time_s'].diff().fillna(0)

            # --- 1. VOLTAGE ADJUSTMENT & FILTERING ---
            df['Adjusted_Voltage_V'] = df['Voltage_V'] - 1.5
            df['Filtered_Voltage_V'] = df['Adjusted_Voltage_V'].rolling(window=30, min_periods=1).mean()
            df['Filtered_Voltage_V'] = df['Filtered_Voltage_V'].clip(lower=0)

            # --- 2. CURRENT BIAS CALCULATION ---
            baseline_offset = df['Current_A'].head(5).mean()
            df['Adjusted_Current_A'] = df['Current_A'] - baseline_offset + 0.5

            # --- 3. FILTER CURRENT ---
            df['Filtered_Current_A'] = df['Adjusted_Current_A'].rolling(window=30, min_periods=1).mean()

            # --- 4. ENERGY CALCULATION ---
            df['Power_W'] = df['Filtered_Voltage_V'] * df['Filtered_Current_A']
            df['Energy_Step_J'] = df['Power_W'] * dt
            df['Cumulative_Energy_J'] = df['Energy_Step_J'].cumsum()
            total_energy = df['Cumulative_Energy_J'].iloc[-1]

            # --- Append the calculated energy to our summary list ---
            summary_data.append({
                'csv name': file_name,
                'cumulative energy': total_energy
            })

            # --- 5. PLOTTING WITH PLOTLY ---
            fig = make_subplots(
                rows=2, cols=1,
                shared_xaxes=True,
                vertical_spacing=0.12,
                specs=[[{"secondary_y": True}],
                       [{"secondary_y": False}]]
            )

            # Primary Axis: Voltage
            fig.add_trace(
                go.Scatter(x=df['Time_s'], y=df['Filtered_Voltage_V'], name='Voltage (V)',
                           line=dict(color='#E13F29', width=3)),
                row=1, col=1, secondary_y=False
            )

            # Secondary Axis: Current
            fig.add_trace(
                go.Scatter(x=df['Time_s'], y=df['Filtered_Current_A'], name='Current (A)',
                           line=dict(color='#006BCC', width=3)),
                row=1, col=1, secondary_y=True
            )

            # Bottom Subplot: Cumulative Energy (Purple)
            fig.add_trace(
                go.Scatter(x=df['Time_s'], y=df['Cumulative_Energy_J'], name='Energy (J)',
                           line=dict(color='#8E44AD', width=3)),
                row=2, col=1
            )

            # --- FORMATTING & LAYOUT ---
            axis_style = dict(
                showline=True, linewidth=2, linecolor='black',
                showgrid=True, gridwidth=1, gridcolor='#E5E5E5',
                zeroline=True, zerolinewidth=1.5, zerolinecolor='black',
                mirror=True
            )

            t_font = dict(family="Arial", size=24)
            tk_font = dict(family="Arial", size=18)

            fig.update_layout(
                title=dict(
                    text=f"<b>Electrical Data Analysis: {file_name}</b><br><span style='font-size: 18px;'>Calculated Bias: {baseline_offset:.4f}A | Total Energy: {total_energy:.2f} J</span>",
                    font=dict(family="Arial", size=32, color="black"),
                    x=0.5,
                    y=0.96
                ),
                font=dict(family="Arial", size=24, color="black"),
                paper_bgcolor='white',
                plot_bgcolor='white',
                width=1700,
                height=800,
                legend=dict(
                    x=1.05, y=1,
                    bordercolor="black", borderwidth=1.5,
                    font=dict(family="Arial", size=20, color="black")
                ),
                margin=dict(t=120, b=50, l=80, r=80)
            )

            fig.update_xaxes(title_text="Time (Seconds)", row=2, col=1, title_font=dict(**t_font, color='black'),
                             tickfont=dict(**tk_font, color='black'), **axis_style)
            fig.update_xaxes(tickfont=dict(**tk_font, color='black'), **axis_style, row=1, col=1)

            fig.update_yaxes(title_text="Voltage (V)", row=1, col=1, secondary_y=False,
                             title_font=dict(**t_font, color='black'), tickfont=dict(**tk_font, color='black'),
                             **axis_style)
            fig.update_yaxes(title_text="Current (A)", row=1, col=1, secondary_y=True,
                             title_font=dict(**t_font, color='black'), tickfont=dict(**tk_font, color='black'),
                             **axis_style)
            fig.update_yaxes(title_text="Cumulative Energy (J)", row=2, col=1, title_font=dict(**t_font, color='black'),
                             tickfont=dict(**tk_font, color='black'), **axis_style)

            # --- SAVE FILES ---
            html_path = os.path.join(output_folder, file_name.replace('.csv', '_energy_analysis.html'))
            fig.write_html(html_path)
            print(f"Saved HTML to: {html_path}")

            try:
                svg_path = os.path.join(output_folder, file_name.replace('.csv', '_energy_analysis.png'))
                fig.write_image(svg_path)
                print(f"Saved SVG to: {svg_path}")
            except Exception as ex:
                print(f"Failed to save SVG for {file_name}. Ensure 'kaleido' is installed. Error: {ex}")

        except Exception as e:
            print(f"Error processing {file_name}: {e}")

    # --- EXPORT SUMMARY CSV ---
    if summary_data:
        summary_df = pd.DataFrame(summary_data)
        summary_csv_path = os.path.join(output_folder, "energy_summary.csv")
        summary_df.to_csv(summary_csv_path, index=False)
        print(f"\nSaved Summary CSV to: {summary_csv_path}")


if __name__ == "__main__":
    input_dir = r'D:\PREMALab\Mass-Shift\Code\Python\MultiTerr'
    output_dir = r'D:\PREMALab\Mass-Shift\Code\Python\MultiTerr'

    plot_csv_files_plotly(input_dir, output_dir)
'''

import pandas as pd
import plotly.graph_objects as go
import numpy as np


def process_and_plot_liquid_glass(csv_path, output_html):
    # 1. Load data
    df = pd.read_csv(csv_path)

    # 2. Extract category from filename safely
    def get_category(filename):
        name = str(filename).lower()
        if 'head' in name:
            return 'head'
        elif 'mid' in name:
            return 'mid'
        elif 'tail' in name:
            return 'tail'
        elif 'ht' in name:
            return 'ht'
        elif 'th' in name:
            return 'th'
        else:
            return 'other'

    df['category'] = df['csv name'].apply(get_category)
    df = df[df['category'] != 'other']

    # 3. Calculate mean and std deviation
    summary = df.groupby('category')['cumulative energy'].agg(['mean', 'std']).reset_index()

    # 4. Define specific categories and order
    ordered_cats = ['head', 'mid', 'tail', 'ht', 'th']
    summary['category'] = pd.Categorical(summary['category'], categories=ordered_cats, ordered=True)
    summary = summary.sort_values('category').dropna()

    cats = summary['category'].tolist()
    means = summary['mean'].fillna(0).tolist()
    stds = summary['std'].fillna(0).tolist()

    # 5. Split the 150 Joules into a separate internal stack
    base_energy = []
    pump_energy = []
    std_base = []
    std_pump = []

    for c, m, s in zip(cats, means, stds):
        if c in ['ht', 'th']:
            # Allocate 150 for the pump, the remainder stays in the base
            p = 150.0
            b = max(0, m - p)  # Prevents negative values if total < 150
            base_energy.append(b)
            pump_energy.append(p)
            std_base.append(0)  # No error bar on the bottom
            std_pump.append(s)  # Error bar goes on the top stack
        else:
            # All energy is base energy
            base_energy.append(m)
            pump_energy.append(0.0)
            std_base.append(s)  # Error bar goes on the top stack
            std_pump.append(0)  # No error bar on the empty pump stack

    # Original specific colors converted to solid hex for clear SVG rendering
    base_colors = {
        'head': '#e13f29',  # Red
        'mid': '#006bcc',  # Blue
        'tail': '#8e44ad',  # Purple
        'ht': '#2ecc71',  # Green
        'th': '#f1c40f'  # Yellow
    }

    fig = go.Figure()

    # --- TRACE 1: Base Locomotion Energy ---
    fig.add_trace(go.Bar(
        name='Locomotion Energy',
        x=cats,
        y=base_energy,
        # The thick, upward-only error bars applied cleanly
        error_y=dict(
            type='data',
            array=std_base,
            symmetric=False,
            arrayminus=[0] * len(std_base),
            visible=True,
            thickness=4,
            width=16,
            color='black'
        ),
        marker_color=[base_colors.get(c, '#000000') for c in cats],
        marker_line_color='black',
        marker_line_width=2
    ))

    # --- TRACE 2: Pump Energy Portion ---
    fig.add_trace(go.Bar(
        name='Energy Consumed by Pump',
        x=cats,
        y=pump_energy,
        error_y=dict(
            type='data',
            array=std_pump,
            symmetric=False,
            arrayminus=[0] * len(std_pump),
            visible=True,
            thickness=4,
            width=16,
            color='black'
        ),
        marker_color='#d3d3d3',  # A clean light grey distinguishes the pump power
        marker_line_color='black',
        marker_line_width=2
    ))

    # --- TYPOGRAPHY & CANVAS RULES (1080p Standardized Style) ---
    fig.update_layout(
        barmode='stack',
        title=dict(text="<b>Average Energy by Category</b>", font=dict(size=32)),
        xaxis_title=dict(text="Configuration", font=dict(size=24)),
        yaxis_title=dict(text="Energy (J)", font=dict(size=24)),
        plot_bgcolor='white',
        paper_bgcolor='white',
        font=dict(family="Arial, sans-serif", color="black", size=20),
        width=1600,
        height=1080,
        margin=dict(l=80, r=80, t=100, b=80),
        legend=dict(
            title=dict(text="Energy Distribution", font=dict(size=24)),
            bordercolor="black",
            borderwidth=1,
            x=1.02,
            y=1,
            font=dict(size=20)
        )
    )

    # Clean and style axes precisely to the previous chart
    fig.update_xaxes(
        showline=True, linewidth=2, linecolor='black',
        ticks='outside', mirror=True, tickfont=dict(size=20)
    )
    fig.update_yaxes(
        showline=True, linewidth=2, linecolor='black',
        ticks='outside', gridcolor='#e5e5e5', mirror=True, tickfont=dict(size=20)
    )

    # Export both the requested HTML and an SVG counterpart
    svg_out = output_html.replace('.html', '.svg')

    try:
        fig.write_image(svg_out)
        print(f"Chart successfully exported as SVG to: {svg_out}")
    except Exception as e:
        print(f"Could not export SVG (requires kaleido): {e}")

    fig.write_html(output_html)
    print(f"Chart successfully exported as HTML to: {output_html}")


if __name__ == "__main__":
    # Formatted as raw strings (r'') to prevent errors from Windows backslashes
    csv_file = r'D:\PREMALab\Mass-Shift\Code\Python\MultiTerr\energy_summary.csv'
    output_html = r'D:\PREMALab\Mass-Shift\Code\Python\MultiTerr\liquid_glass_bars.html'

    process_and_plot_liquid_glass(csv_file, output_html)