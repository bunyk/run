import streamlit as st
import pandas as pd
from pathlib import Path
import datetime
import matplotlib.pyplot as plt

from tcx import TCX
from db import ActivityDB
from utils import format_pace

st.set_page_config(page_title="Dashboard")

def format_duration(duration):
    return str(datetime.timedelta(seconds=duration.total_seconds()))

def main():
    # Get all activities from DB
    with ActivityDB() as db:
        activities = db.get_activities()

    if not activities:
        st.warning("No activities found in database")
        return

    # Convert to DataFrame
    df = pd.DataFrame(activities)

    df['start_time'] = pd.to_datetime(df['start_time'])
    for field in ['duration', 'best_100', 'best_1k', 'best_3200', 'best_5k', 'best_10k']:
        df[field] = pd.to_timedelta(df[field], unit='s')

    activity_types = ['All'] + df['type'].unique().tolist()
    selected_type = st.selectbox("Type:", activity_types)
    if selected_type != 'All':
        df = df[df['type'] == selected_type]

    st.header("Total")
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Activities", len(df))
    with col2:
        st.metric("Distance", f"{df['distance'].sum() / 1000:.1f} km")
    with col3:
         st.metric("Duration", format_duration(df['duration'].sum()))

    # Best times summaries
    st.subheader("🏆 Best Times")
    best_times = []
    for name, col in [("100m", "best_100"), ("1km", "best_1k"), ("3200m", "best_3200"), ("5km", "best_5k"), ("10km", "best_10k")]:
        val = df[df[col].notna()][col].min()
        best_times.append((name, format_duration(val) if pd.notna(val) else "N/A"))
    
    st.markdown("| Record | Time |\n|--------|------|\n" + "\n".join(f"| {name} | {time} |" for name, time in best_times))

    # --- Charts ---
    st.header("📊 Trends")
    
    col1, col2 = st.columns(2)
    with col1:
        aggregation = st.selectbox("Aggregation:", ["Daily", "Weekly", "Monthly"])
    with col2:
        metrics = ['duration', 'distance', 'best_100', 'best_1k', 'best_3200', 'best_5k', 'best_10k']
        selected_metric = st.selectbox("Metric:", metrics)
    
    # Aggregate data
    chart_data = aggregate_data(df, aggregation, selected_metric)
    
    if len(chart_data) > 0:
        # Format the chart based on metric type
        fig, ax = plt.subplots()
        
        if selected_metric == 'distance':
            y_values = chart_data['value'] / 1000  # Convert to km
            y_label = "Distance (km)"
        else:
            # duration
            y_values = chart_data['value'].apply(lambda x: x.total_seconds())
            ax.yaxis.set_major_formatter(durationFormatter)
            y_label = selected_metric
        
        ax.bar(chart_data['period'].astype(str), y_values)
        ax.set_xlabel('Period')
        ax.set_ylabel(y_label)
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        st.pyplot(fig)
    else:
        st.info(f"No data available for {selected_metric} with {aggregation} aggregation")

    # --- Activities Table ---
    st.header("📋 Activities")

    # Filter by type

    # Display DataFrame
    st.dataframe(df, hide_index=True, column_config={
        'start_time': st.column_config.DateColumn("Start Time"),
        'filename': None,
    })


def duration_format_func(x, pos, zfill=False):
    parts = []
    hours = int(x//3600)
    minutes = int((x%3600)//60)
    seconds = int(x%60)
    if hours > 0 or zfill:
        parts.append(f"{hours}")
    if minutes > 0 or hours > 0 or zfill:
        parts.append(f"{minutes:02d}")

    parts.append(f"{seconds:02d}")
    return ":".join(parts)

from matplotlib.ticker import FuncFormatter
durationFormatter = FuncFormatter(duration_format_func)

def aggregate_data(df, aggregation, metric):
    """Aggregate data by time period for a given metric."""
    df = df.copy()
    df['date'] = df['start_time'].dt.date

    if aggregation == 'Daily':
        grouped = df.groupby('date')
        all_periods = pd.date_range(
            start=df['date'].min(),
            end=df['date'].max(),
            freq='D'
        ).date
    elif aggregation == 'Weekly':
        df['week'] = df['start_time'].dt.to_period('W').dt.start_time.dt.date
        grouped = df.groupby('week')
        all_periods = pd.date_range(
            start=df['date'].min(),
            end=df['date'].max(),
            freq='W'
        ).date
    else:  # Monthly
        df['month'] = df['start_time'].dt.to_period('M').dt.start_time.dt.date
        grouped = df.groupby('month')
        all_periods = pd.date_range(
            start=df['date'].min(),
            end=df['date'].max(),
            freq='MS'
        ).date

    if metric == 'duration':
        aggregated = grouped['duration'].sum().reset_index()
        aggregated.columns = ['period', 'value']
    elif metric == 'distance':
        aggregated = grouped['distance'].sum().reset_index()
        aggregated.columns = ['period', 'value']
    else:  # best times - take minimum (best) for each period
        best_col = metric  # e.g., 'best_100', 'best_1k'
        aggregated = grouped[best_col].min().reset_index()
        aggregated.columns = ['period', 'value']
        # Drop rows with NaN values
        aggregated = aggregated.dropna()

    # Create complete date series
    complete = pd.DataFrame({'period': all_periods})
    result = complete.merge(aggregated, on='period', how='left')

    return result

if __name__ == '__main__':
    main()
