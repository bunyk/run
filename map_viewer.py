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
    st.title("A run")

    data_dir = Path('data')
    tcx_files = list(data_dir.glob('*.tcx'))

    # Add page selection in sidebar
    page = st.sidebar.radio("Page", ["Single Run", "Summary"])

    if page == "Summary":
        st.write("Summary page - TODO")
        return

    if not tcx_files:
        st.warning("No TCX files found in the data/ directory.")
        return

    # File selection
    selected_file = st.sidebar.selectbox("Select a TCX file:", [f.name for f in tcx_files])
    tcx_path = data_dir / selected_file
    st.markdown(selected_file)

    # Parse TCX file
    with st.spinner("Parsing TCX file..."):
        tcx = TCX(tcx_path)

    # Display map if coordinates available
    coords = tcx.coordinates
    if coords:
        df_map = pd.DataFrame(coords, columns=['latitude', 'longitude'])
        st.map(df_map, latitude='latitude', longitude='longitude', size=2)

    # Activity Summary
    st.markdown("### Activity Summary\n\n")

    if tcx.activity_type:
        st.markdown(f"**Activity Type:** {tcx.activity_type}\n\n")

    duration = tcx.duration
    st.markdown(f"**Duration:** {format_time(duration)}\n\n")

    total_distance = tcx.total_distance
    st.markdown(f"**Distance:** {total_distance:.2f} m\n\n")

    avg_speed = tcx.avg_speed
    st.markdown(f"**Average Speed:** {avg_speed:.2f} km/h\n\n")

    top_speed = tcx.top_speed()
    st.markdown(f"**Top Speed:** {top_speed:.2f} km/h\n\n")


if __name__ == '__main__':
    main()
