import streamlit as st
import pandas as pd
from pathlib import Path
import datetime

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

    print('dtypes', df.dtypes)
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
    col1, col2, col3, col4, col5 = st.columns(5)
    with col1:
        best_100 = df[df['best_100'].notna()]['best_100'].min()
        st.metric("100m", format_duration(best_100) if pd.notna(best_100) else "N/A")
    with col2:
        best_1k = df[df['best_1k'].notna()]['best_1k'].min()
        st.metric("1km", format_duration(best_1k) if pd.notna(best_1k) else "N/A")
    with col3:
        best_3200 = df[df['best_3200'].notna()]['best_3200'].min()
        st.metric("3200m", format_duration(best_3200) if pd.notna(best_3200) else "N/A")
    with col4:
        best_5k = df[df['best_5k'].notna()]['best_5k'].min()
        st.metric("5km", format_duration(best_5k) if pd.notna(best_5k) else "N/A")
    with col5:
        best_10k = df[df['best_10k'].notna()]['best_10k'].min()
        st.metric("10km", format_duration(best_10k) if pd.notna(best_10k) else "N/A")

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
        if selected_metric == 'duration':
            chart_data['display_value'] = chart_data['value']
            st.bar_chart(chart_data.set_index('period')['display_value'], use_container_width=True)
        elif selected_metric == 'distance':
            chart_data['display_value'] = chart_data['value'] / 1000  # Convert to km
            st.bar_chart(chart_data.set_index('period')['display_value'], use_container_width=True)
        else:
            # For best times, convert to minutes for better readability
            chart_data['display_value'] = chart_data['value'] / 60
            st.bar_chart(chart_data.set_index('period')['display_value'], use_container_width=True)
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

def aggregate_data(df, aggregation, metric):
    """Aggregate data by time period for a given metric."""
    df = df.copy()
    df['date'] = df['start_time'].dt.date
    
    if aggregation == 'Daily':
        grouped = df.groupby('date')
    elif aggregation == 'Weekly':
        df['week'] = df['start_time'].dt.to_period('W').dt.start_time
        grouped = df.groupby('week')
    else:  # Monthly
        df['month'] = df['start_time'].dt.to_period('M').dt.start_time
        grouped = df.groupby('month')
    
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
    
    return aggregated


if __name__ == '__main__':
    main()
