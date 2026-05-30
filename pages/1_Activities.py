import streamlit as st
import pandas as pd
from pathlib import Path

from tcx import TCX
from utils import format_time

st.set_page_config(page_title="Activities")


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
    for dst in [100, 1000, 3200, 5000, 10000]:
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
    
    # Calculate window size for running average (roughly 5 seconds worth or 10% of points)
    window = max(3, min(len(df) // 10, 30))
    
    # Create separate line charts for each available metric with running average
    for col in ['Speed', 'Cadence', 'HeartRate']:
        if col in df.columns:
            df_clean = df.dropna(subset=[col])
            df_clean[col] = df_clean[col].rolling(window=window, min_periods=1, center=True).mean()
            if len(df_clean) > 1:
                st.line_chart(df_clean, x='Time', y=[col])


if __name__ == '__main__':
    main()
