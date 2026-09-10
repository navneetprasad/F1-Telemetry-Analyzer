import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import streamlit as st
import fastf1
from fastf1 import plotting

st.set_page_config(page_title="F1 Telemetry Analyzer (Up to 2026)", layout="wide")

# Enable FastF1 Local Cache
cache_dir = './f1_cache'
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)
plotting.setup_mpl(mpl_timedelta_support=False, misc_mpl_mods=False)

# Comprehensive reference roster for formatting
ROSTER_NAMES = {
    'VER': 'Max Verstappen',
    'NOR': 'Lando Norris',
    'LEC': 'Charles Leclerc',
    'HAM': 'Lewis Hamilton',
    'RUS': 'George Russell',
    'PIA': 'Oscar Piastri',
    'SAI': 'Carlos Sainz',
    'ALO': 'Fernando Alonso',
    'STR': 'Lance Stroll',
    'GAS': 'Pierre Gasly',
    'OCO': 'Esteban Ocon',
    'ALB': 'Alexander Albon',
    'TSU': 'Yuki Tsunoda',
    'HUL': 'Nico Hülkenberg',
    'BOT': 'Valtteri Bottas',
    'PER': 'Sergio Pérez',
    'LAW': 'Liam Lawson',
    'ANT': 'Andrea Kimi Antonelli',
    'BEA': 'Oliver Bearman',
    'BOR': 'Gabriel Bortoleto',
    'DOO': 'Jack Doohan',
    'COL': 'Franco Colapinto',
    'HAD': 'Isack Hadjar',
    'LIN': 'Arvid Lindblad',
    'ZHO': 'Guanyu Zhou',
    'MAG': 'Kevin Magnussen',
    'SAR': 'Logan Sargeant',
    'RIC': 'Daniel Ricciardo',
    'DEV': 'Nyck de Vries',
    'VET': 'Sebastian Vettel',
    'RAI': 'Kimi Räikkönen',
    'GIO': 'Antonio Giovinazzi',
    'LAT': 'Nicholas Latifi',
    'MSC': 'Mick Schumacher',
    'MAZ': 'Nikita Mazepin',
    'KVY': 'Daniil Kvyat',
    'GRO': 'Romain Grosjean'
}

# ---------------------------------------------------------
# Sidebar: Session Configuration
# ---------------------------------------------------------
st.sidebar.header("1. Choose Grand Prix Session")
selected_year = st.sidebar.slider("Year", min_value=2018, max_value=2026, value=2025, step=1)

# Dynamically load the race calendar for the chosen year
@st.cache_data(show_spinner=False)
def get_event_schedule(year_val):
    try:
        schedule = fastf1.get_event_schedule(year_val)
        # Filter out preseason testing rows
        real_events = schedule[schedule['EventFormat'] != 'testing']['EventName'].tolist()
        return real_events if len(real_events) > 0 else ["Monza", "Silverstone", "Bahrain", "Spa"]
    except Exception:
        return ["Monza", "Silverstone", "Spa", "Monaco", "Bahrain", "Suzuka"]

calendar = get_event_schedule(selected_year)
selected_event = st.sidebar.selectbox("Grand Prix", calendar, index=0 if "Monza" not in calendar else calendar.index("Monza"))
selected_session = st.sidebar.selectbox("Session Type", ["Q", "R", "SQ", "FP1", "FP2", "FP3"], index=0)

# ---------------------------------------------------------
# Data Loading & Driver Extraction
# ---------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_session(yr, gp, ses):
    session = fastf1.get_session(yr, gp, ses)
    session.load(telemetry=True, weather=False)
    return session

with st.spinner(f"Loading {selected_year} {selected_event} session metadata..."):
    try:
        session = load_session(selected_year, selected_event, selected_session)
        session_loaded = True
    except Exception as e:
        session_loaded = False
        st.sidebar.error(f"Could not load session: {e}")

# Build driver dropdown list dynamically from the loaded session
driver_options = []
code_lookup = {}

if session_loaded:
    results_df = session.results
    if not results_df.empty and 'Abbreviation' in results_df.columns:
        for _, row in results_df.iterrows():
            code = str(row['Abbreviation']).strip().upper()
            full_name = str(row.get('FullName', ROSTER_NAMES.get(code, code)))
            label = f"{code} ({full_name})"
            driver_options.append(label)
            code_lookup[label] = code
    else:
        # Fallback to lap entries
        present_drivers = session.laps['Driver'].unique().tolist()
        for code in present_drivers:
            name = ROSTER_NAMES.get(code, code)
            label = f"{code} ({name})"
            driver_options.append(label)
            code_lookup[label] = code
else:
    # Standby roster if session fails or is loading
    for code, full_name in sorted(ROSTER_NAMES.items()):
        label = f"{code} ({full_name})"
        driver_options.append(label)
        code_lookup[label] = code

st.sidebar.header("2. Driver Selection")

# Pre-select LEC and HAM if available, else first two
default_d1_idx = 0
default_d2_idx = 1 if len(driver_options) > 1 else 0

for i, opt in enumerate(driver_options):
    if opt.startswith("LEC"):
        default_d1_idx = i
    elif opt.startswith("HAM"):
        default_d2_idx = i

sel_driver1_label = st.sidebar.selectbox("Driver 1 (Reference)", driver_options, index=default_d1_idx)
sel_driver2_label = st.sidebar.selectbox("Driver 2 (Comparison)", driver_options, index=default_d2_idx)

driver1 = code_lookup[sel_driver1_label]
driver2 = code_lookup[sel_driver2_label]

run_analysis = st.sidebar.button("Analyze Telemetry", type="primary")

# ---------------------------------------------------------
# Telemetry Processing & Rendering
# ---------------------------------------------------------
if session_loaded and (run_analysis or 'ran_once' in st.session_state):
    st.session_state['ran_once'] = True

    try:
        # 1. Filter laps for each driver and remove invalid / deleted laps
        laps_d1 = session.laps.pick_drivers(driver1).pick_quicklaps()
        laps_d2 = session.laps.pick_drivers(driver2).pick_quicklaps()

        if laps_d1.empty or laps_d2.empty:
            st.warning(f"No valid timed quick-laps found for either {driver1} or {driver2} in this session.")
            st.stop()

        # 2. Pick fastest lap safely
        lap_d1 = laps_d1.pick_fastest()
        lap_d2 = laps_d2.pick_fastest()

        if lap_d1 is None or lap_d2 is None or pd.isna(lap_d1['LapTime']) or pd.isna(lap_d2['LapTime']):
            st.error(f"Could not retrieve a valid fastest lap time for both drivers ({driver1}: {lap_d1}, {driver2}: {lap_d2}). Try another session.")
            st.stop()

        t1_sec = lap_d1['LapTime'].total_seconds()
        t2_sec = lap_d2['LapTime'].total_seconds()
        lap_delta = t2_sec - t1_sec  # Positive means D1 was faster

        # Metrics Banner
        col1, col2, col3 = st.columns(3)
        col1.metric(
            label=f"{sel_driver1_label}", 
            value=str(lap_d1['LapTime'])[10:19], 
            delta=f"{-lap_delta:.3f}s" if lap_delta < 0 else None
        )
        col2.metric(
            label=f"{sel_driver2_label}", 
            value=str(lap_d2['LapTime'])[10:19], 
            delta=f"{lap_delta:.3f}s" if lap_delta > 0 else None
        )
        col3.metric(
            label="Lap Delta", 
            value=f"{abs(lap_delta):.3f}s", 
            delta=f"{driver1} Faster" if lap_delta > 0 else f"{driver2} Faster"
        )

        # Extract Official Sector Times
        s1_d1 = lap_d1['Sector1Time'].total_seconds() if pd.notna(lap_d1['Sector1Time']) else 0
        s2_d1 = lap_d1['Sector2Time'].total_seconds() if pd.notna(lap_d1['Sector2Time']) else 0
        s3_d1 = lap_d1['Sector3Time'].total_seconds() if pd.notna(lap_d1['Sector3Time']) else 0

        s1_d2 = lap_d2['Sector1Time'].total_seconds() if pd.notna(lap_d2['Sector1Time']) else 0
        s2_d2 = lap_d2['Sector2Time'].total_seconds() if pd.notna(lap_d2['Sector2Time']) else 0
        s3_d2 = lap_d2['Sector3Time'].total_seconds() if pd.notna(lap_d2['Sector3Time']) else 0

        sector_summary = pd.DataFrame({
            'Sector': ['Sector 1', 'Sector 2', 'Sector 3', 'Total Lap'],
            f"{driver1} (s)": [f"{s1_d1:.3f}", f"{s2_d1:.3f}", f"{s3_d1:.3f}", f"{t1_sec:.3f}"],
            f"{driver2} (s)": [f"{s1_d2:.3f}", f"{s2_d2:.3f}", f"{s3_d2:.3f}", f"{t2_sec:.3f}"],
            'Delta (s)': [f"{s1_d2 - s1_d1:+.3f}", f"{s2_d2 - s2_d1:+.3f}", f"{s3_d2 - s3_d1:+.3f}", f"{lap_delta:+.3f}"]
        })

        st.markdown("### Official Sector Timing Breakdown")
        st.dataframe(sector_summary, use_container_width=True, hide_index=True)

        # 3. Safely extract telemetry streams
        tel_d1 = lap_d1.get_telemetry()
        tel_d2 = lap_d2.get_telemetry()

        if tel_d1.empty or tel_d2.empty:
            st.error("Telemetry streams are missing for one or both of the chosen laps.")
            st.stop()

        tel_d1 = tel_d1.add_distance()
        tel_d2 = tel_d2.add_distance()

        # 4. Safe Cumulative Delta Time Calculation
        try:
            delta_res = fastf1.utils.delta_time(lap_d1, lap_d2)
            if delta_res is None or delta_res[0] is None:
                raise ValueError("delta_time returned None")
            delta_t, ref_tel, _ = delta_res
            delta_dist = ref_tel['Distance']
        except Exception:
            # Fallback numeric integration: dt = ds / v
            max_common_dist = min(tel_d1['Distance'].max(), tel_d2['Distance'].max())
            common_dist = np.linspace(0, max_common_dist, 1500)
            s1_ms = np.interp(common_dist, tel_d1['Distance'], tel_d1['Speed']) / 3.6
            s2_ms = np.interp(common_dist, tel_d2['Distance'], tel_d2['Speed']) / 3.6
            s1_ms = np.maximum(s1_ms, 1.0)
            s2_ms = np.maximum(s2_ms, 1.0)
            ds = np.gradient(common_dist)
            delta_t = np.cumsum((1.0 / s2_ms - 1.0 / s1_ms) * ds)
            delta_dist = common_dist

        # Compute Mini-Sectors for Track Dominance
        num_minisectors = 120
        total_dist = min(tel_d1['Distance'].max(), tel_d2['Distance'].max())
        minisector_len = total_dist / num_minisectors

        tel_d1['MiniSector'] = (tel_d1['Distance'] // minisector_len).astype(int)
        tel_d2['MiniSector'] = (tel_d2['Distance'] // minisector_len).astype(int)

        s1_mean = tel_d1.groupby('MiniSector')['Speed'].mean()
        s2_mean = tel_d2.groupby('MiniSector')['Speed'].mean()

        dominance = pd.DataFrame({'s1': s1_mean, 's2': s2_mean}).dropna()
        dominance['Fastest'] = np.where(dominance['s1'] >= dominance['s2'], driver1, driver2)
        tel_map = tel_d1.merge(dominance[['Fastest']], left_on='MiniSector', right_index=True)

        # Dynamic Color Assigning
        try:
            color_d1 = fastf1.plotting.get_driver_color(driver1, session=session)
        except Exception:
            color_d1 = '#E80020'

        try:
            color_d2 = fastf1.plotting.get_driver_color(driver2, session=session)
        except Exception:
            color_d2 = '#00A19B'

        if color_d1 == color_d2:
            color_d2 = '#FFD700'  # Visual contrast for teammates

        # Combined Plot
        fig = plt.figure(figsize=(19, 10))
        outer_gs = gridspec.GridSpec(1, 2, width_ratios=[1.35, 1], wspace=0.15)
        inner_gs = gridspec.GridSpecFromSubplotSpec(4, 1, subplot_spec=outer_gs[0], 
                                                    height_ratios=[1.4, 2.2, 1, 1], hspace=0.1)

        ax_delta_t = fig.add_subplot(inner_gs[0])
        ax_speed = fig.add_subplot(inner_gs[1], sharex=ax_delta_t)
        ax_throttle = fig.add_subplot(inner_gs[2], sharex=ax_delta_t)
        ax_brake = fig.add_subplot(inner_gs[3], sharex=ax_delta_t)
        ax_track = fig.add_subplot(outer_gs[1])

        # 1. Delta Time (s)
        ax_delta_t.plot(delta_dist, delta_t, color='white', lw=1.5)
        ax_delta_t.axhline(0, color='gray', linestyle='--', alpha=0.6)
        ax_delta_t.fill_between(delta_dist, delta_t, 0, where=(delta_t > 0), facecolor=color_d1, alpha=0.4, label=f'{driver1} Ahead')
        ax_delta_t.fill_between(delta_dist, delta_t, 0, where=(delta_t < 0), facecolor=color_d2, alpha=0.4, label=f'{driver2} Ahead')
        ax_delta_t.set_ylabel('Δt (s)', fontsize=10)
        ax_delta_t.legend(loc='upper left', fontsize=8)
        ax_delta_t.grid(True, linestyle=':', alpha=0.5)
        plt.setp(ax_delta_t.get_xticklabels(), visible=False)

        # 2. Speed Traces
        ax_speed.plot(tel_d1['Distance'], tel_d1['Speed'], color=color_d1, lw=1.5, label=driver1)
        ax_speed.plot(tel_d2['Distance'], tel_d2['Speed'], color=color_d2, lw=1.5, linestyle='--', label=driver2)
        ax_speed.set_ylabel('Speed (km/h)', fontsize=10)
        ax_speed.legend(loc='lower left', fontsize=8)
        ax_speed.grid(True, linestyle=':', alpha=0.5)
        plt.setp(ax_speed.get_xticklabels(), visible=False)

        # 3. Throttle
        ax_throttle.plot(tel_d1['Distance'], tel_d1['Throttle'], color=color_d1, lw=1.3)
        ax_throttle.plot(tel_d2['Distance'], tel_d2['Throttle'], color=color_d2, lw=1.3, linestyle='--')
        ax_throttle.set_ylabel('Throttle %', fontsize=10)
        ax_throttle.grid(True, linestyle=':', alpha=0.5)
        plt.setp(ax_throttle.get_xticklabels(), visible=False)

        # 4. Brake
        ax_brake.plot(tel_d1['Distance'], tel_d1['Brake'], color=color_d1, lw=1.3)
        ax_brake.plot(tel_d2['Distance'], tel_d2['Brake'], color=color_d2, lw=1.3, linestyle='--')
        ax_brake.set_ylabel('Brake', fontsize=10)
        ax_brake.set_xlabel('Lap Distance (meters)', fontsize=10)
        ax_brake.grid(True, linestyle=':', alpha=0.5)

        # 5. Track Map
        for drv, clr in [(driver1, color_d1), (driver2, color_d2)]:
            sub = tel_map[tel_map['Fastest'] == drv]
            ax_track.scatter(sub['X'], sub['Y'], c=clr, s=14, label=f"{drv} Advantage", alpha=0.9)

        ax_track.axis('equal')
        ax_track.axis('off')
        ax_track.legend(loc='lower center', frameon=True, fontsize=9)
        ax_track.set_title("Track Mini-Sector Advantage", fontsize=11, weight='bold')

        st.pyplot(fig)

    except Exception as err:
        st.error(f"Error computing comparison: {err}")