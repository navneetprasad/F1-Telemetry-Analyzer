import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import fastf1
from fastf1 import plotting

# 1. Enable caching
cache_dir = './f1_cache'
os.makedirs(cache_dir, exist_ok=True)
fastf1.Cache.enable_cache(cache_dir)

# 2. Setup plotting styles
plotting.setup_mpl(mpl_timedelta_support=False, misc_mpl_mods=False)

# 3. Load Session Data (2025 Italian GP Qualifying)
YEAR = 2025
CIRCUIT = 'Monza'
SESSION_TYPE = 'Q'

print(f"Loading {YEAR} {CIRCUIT} {SESSION_TYPE} session...")
session = fastf1.get_session(YEAR, CIRCUIT, SESSION_TYPE)
session.load(telemetry=True, weather=False)

# 4. Extract Fastest Laps for Both Teammates
d1, d2 = 'LEC', 'HAM'
lap_d1 = session.laps.pick_drivers(d1).pick_fastest()
lap_d2 = session.laps.pick_drivers(d2).pick_fastest()

# 5. Extract Telemetry Streams & Add Distance
tel_d1 = lap_d1.get_telemetry().add_distance()
tel_d2 = lap_d2.get_telemetry().add_distance()

# 6. Distance-based Speed Delta Interpolation
common_distance = np.linspace(0, min(tel_d1['Distance'].max(), tel_d2['Distance'].max()), 1500)
speed_d1_interp = np.interp(common_distance, tel_d1['Distance'], tel_d1['Speed'])
speed_d2_interp = np.interp(common_distance, tel_d2['Distance'], tel_d2['Speed'])
speed_delta = speed_d1_interp - speed_d2_interp

# 7. Mini-Sector Dominance Calculation
num_minisectors = 100
total_dist = min(tel_d1['Distance'].max(), tel_d2['Distance'].max())
minisector_length = total_dist / num_minisectors

tel_d1['MiniSector'] = (tel_d1['Distance'] // minisector_length).astype(int)
tel_d2['MiniSector'] = (tel_d2['Distance'] // minisector_length).astype(int)

s1 = tel_d1.groupby('MiniSector')['Speed'].mean()
s2 = tel_d2.groupby('MiniSector')['Speed'].mean()

dominance = pd.DataFrame({'s1': s1, 's2': s2}).dropna()
dominance['Fastest'] = np.where(dominance['s1'] > dominance['s2'], d1, d2)
tel_merged = tel_d1.merge(dominance[['Fastest']], left_on='MiniSector', right_index=True)

# 8. Build Combined Figure using GridSpec
color_d1 = '#E80020'  # Ferrari Red
color_d2 = '#FFD700'  # Yellow accent

fig = plt.figure(figsize=(18, 9))
fig.suptitle(f"{YEAR} {CIRCUIT} GP — Qualifying Telemetry & Mini-Sector Dominance\n{d1} ({lap_d1['LapTime']}) vs {d2} ({lap_d2['LapTime']})", 
             fontsize=14, weight='bold')

# Outer grid: 1 row, 2 columns (Left: Telemetry traces, Right: Track map)
outer_gs = gridspec.GridSpec(1, 2, width_ratios=[1.3, 1], wspace=0.18)

# Left sub-grid: 4 rows for telemetry channels
inner_gs = gridspec.GridSpecFromSubplotSpec(4, 1, subplot_spec=outer_gs[0], 
                                            height_ratios=[2.5, 1.2, 1, 1], hspace=0.1)

ax_speed = fig.add_subplot(inner_gs[0])
ax_delta = fig.add_subplot(inner_gs[1], sharex=ax_speed)
ax_throttle = fig.add_subplot(inner_gs[2], sharex=ax_speed)
ax_brake = fig.add_subplot(inner_gs[3], sharex=ax_speed)

# Right subplot: Circuit map
ax_track = fig.add_subplot(outer_gs[1])

# --- Subplot 1: Speed Overlay ---
ax_speed.plot(tel_d1['Distance'], tel_d1['Speed'], color=color_d1, lw=1.5, label=f"{d1}")
ax_speed.plot(tel_d2['Distance'], tel_d2['Speed'], color=color_d2, lw=1.5, linestyle='--', label=f"{d2}")
ax_speed.set_ylabel('Speed (km/h)', fontsize=10)
ax_speed.legend(loc='upper right', fontsize=9)
ax_speed.grid(True, linestyle=':', alpha=0.5)
plt.setp(ax_speed.get_xticklabels(), visible=False)

# --- Subplot 2: Speed Delta ---
ax_delta.plot(common_distance, speed_delta, color='white', lw=1.2)
ax_delta.axhline(0, color='gray', linestyle='--', alpha=0.6)
ax_delta.fill_between(common_distance, speed_delta, 0, where=(speed_delta > 0), facecolor=color_d1, alpha=0.45)
ax_delta.fill_between(common_distance, speed_delta, 0, where=(speed_delta < 0), facecolor=color_d2, alpha=0.45)
ax_delta.set_ylabel('Δv (km/h)', fontsize=10)
ax_delta.grid(True, linestyle=':', alpha=0.5)
plt.setp(ax_delta.get_xticklabels(), visible=False)

# --- Subplot 3: Throttle Input ---
ax_throttle.plot(tel_d1['Distance'], tel_d1['Throttle'], color=color_d1, lw=1.3)
ax_throttle.plot(tel_d2['Distance'], tel_d2['Throttle'], color=color_d2, lw=1.3, linestyle='--')
ax_throttle.set_ylabel('Throttle %', fontsize=10)
ax_throttle.grid(True, linestyle=':', alpha=0.5)
plt.setp(ax_throttle.get_xticklabels(), visible=False)

# --- Subplot 4: Brake Input ---
ax_brake.plot(tel_d1['Distance'], tel_d1['Brake'], color=color_d1, lw=1.3)
ax_brake.plot(tel_d2['Distance'], tel_d2['Brake'], color=color_d2, lw=1.3, linestyle='--')
ax_brake.set_ylabel('Brake', fontsize=10)
ax_brake.set_xlabel('Lap Distance (meters)', fontsize=10)
ax_brake.grid(True, linestyle=':', alpha=0.5)

# --- Right Panel: 2D Mini-Sector Track Map ---
for driver, clr in [(d1, color_d1), (d2, color_d2)]:
    pts = tel_merged[tel_merged['Fastest'] == driver]
    ax_track.scatter(pts['X'], pts['Y'], c=clr, s=12, label=f"{driver} Faster", alpha=0.9)

ax_track.set_title("Track Mini-Sector Advantage", fontsize=11, weight='bold')
ax_track.axis('equal')
ax_track.axis('off')
ax_track.legend(loc='lower center', frameon=True, fontsize=9)

# Save & Render
plt.tight_layout()
plt.savefig('f1_combined_analysis.png', dpi=300, bbox_inches='tight')
plt.show()