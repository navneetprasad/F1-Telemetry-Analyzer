# 🏎️ F1 Telemetry & Mini-Sector Performance Analyzer

An interactive Formula 1 data analytics dashboard built with Python, FastF1, and Streamlit. This application allows users to analyze real-world telemetry streams, compare driver performance across full Grand Prix weekends, evaluate cumulative delta time ($\Delta t$), and visualize 2D track mini-sector dominance.

---

## 📌 Project Preview

                      <img width="4413" height="2538" alt="image" src="https://github.com/user-attachments/assets/5b667c9a-c8c9-4ae0-b1cc-87766a7e73b9" />


*Figure: Teammate telemetry comparison between Charles Leclerc (LEC) and Lewis Hamilton (HAM) during the 2025 Italian Grand Prix (Monza) Qualifying session.*

---

## 🚀 Features

- **Dynamic Season & Event Coverage (2018–2026):** Fetches official session schedules and driver entry lists directly from the FIA timing feed.
- **Smart Driver Roster:** Dropdown selection matching 3-letter driver abbreviations with full names (e.g., `LEC (Charles Leclerc)`, `HAM (Lewis Hamilton)`).
- **Multi-Channel Telemetry Alignment:** Synchronizes high-frequency asynchronous telemetry feeds along a uniform 1D distance axis ($s$).
- **Cumulative Delta Time ($\Delta t$):** Traces time gained or lost meter-by-meter using numerical velocity integration:
  $$\Delta t(d) = \int_0^d \left( \frac{1}{v_{\text{ref}}(s)} - \frac{1}{v_{\text{comp}}(s)} \right) ds$$
- **2D Mini-Sector Dominance Map:** Segments circuits into 120 spatial zones using GPS ($X, Y$) car coordinates and highlights which driver carried higher mean velocity through every corner and straight.
- **Robust Outlier Filtering:** Automatically screens session data with `.pick_quicklaps()` to discard unrepresentative in-laps, out-laps, and track-limit invalidations.

---

## 🛠️ Tech Stack

- **Data Pipeline:** [`FastF1`](https://github.com/theOehrly/Fast-F1) (official timing/telemetry API wrapper)
- **Data Manipulation:** `Pandas`, `NumPy`
- **Visualization:** `Matplotlib` (GridSpec multi-panel rendering)
- **Application Framework:** `Streamlit`

---

## 📂 Project Structure

```text
F1/
├── assets/
│   └── monza_2025_analysis.jpg      # Sample telemetry visual preview
├── .gitignore                       # Prevents committing heavy API caches
├── app.py                           # Full Streamlit web application
├── README.md                        # Documentation & analysis case study
└── requirements.txt                 # Project dependencies
