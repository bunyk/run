import streamlit as st
import pandas as pd
from pathlib import Path
from datetime import datetime

from tcx import TCX


def format_time(seconds):
    """Format seconds into HH:MM:SS or MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def main():
    data_dir = Path('data')
    tcx_files = list(data_dir.glob('*.tcx'))
    if not tcx_files:
        st.warning("No TCX files found in the data/ directory.")
        return

    # File selection
    selected_file = st.sidebar.selectbox("Select a TCX file:", [f.name for f in tcx_files])
    tcx_path = data_dir / selected_file

    # Parse TCX file
    with st.spinner("Parsing TCX file..."):
        tcx = TCX(tcx_path)

    st.title(tcx.activity_type if tcx.activity_type else "Activity")
    st.markdown(f"**Duration:** {format_time(tcx.duration)}\n\n")
    st.markdown(f"**Distance:** {tcx.distance:.2f} m\n\n")
    st.markdown(f"**Average Speed:** {tcx.avg_speed:.2f} km/h\n\n")

    records = []
    for dst in [100, 1000, 3200, 10000]:
        best_time = tcx.best_time_for_distance(dst)
        if best_time > 0:
            records.append((dst, best_time))

    if records:
        st.markdown('### Best times:\n\n')
        for dst, best_time in records:
            st.markdown(f"* **{dst} m**: {format_time(best_time)}\n\n")


    # Display map if coordinates available
    coords = tcx.coordinates
    if coords:
        df_map = pd.DataFrame(coords, columns=['latitude', 'longitude'])
        st.map(df_map, latitude='latitude', longitude='longitude', size=2)

    # Get trackpoint data and create separate charts for each metric
    df = tcx.get_trackpoint_data()
    
    # Create separate line charts for each available metric
    for col in ['Speed', 'Cadence', 'HeartRate']:
        if col in df.columns:
            df_clean = df.dropna(subset=[col])
            st.line_chart(df_clean, x='Time', y=[col])


if __name__ == '__main__':
    main()
