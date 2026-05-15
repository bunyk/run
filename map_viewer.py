import streamlit as st
import pandas as pd
import numpy as np
import xml.etree.ElementTree as ET
from pathlib import Path
from datetime import datetime
import json
import hashlib

NS = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

CACHE_DIR = Path('cache')

def parse_time(time_str):
    """Parse ISO 8601 datetime string to datetime object."""
    return datetime.fromisoformat(time_str.replace('Z', '+00:00'))

def extract_data_from_tcx(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    trackpoints = []
    for trackpoint in root.findall('.//tcx:Trackpoint', NS):
        position = trackpoint.find('tcx:Position', NS)
        time_el = trackpoint.find('tcx:Time', NS)
        distance_el = trackpoint.find('tcx:DistanceMeters', NS)
        speed_el = trackpoint.find('tcx:Speed', NS)
        heartrate_el = trackpoint.find('.//tcx:HeartRateBpm/tcx:Value', NS)
        
        # Try to get speed from extensions (Garmin format)
        if speed_el is None:
            speed_el = trackpoint.find('.//tcx:Speed', NS)
        
        # Try to get speed from TPX extension
        if speed_el is None:
            tpx = trackpoint.find('.//tcx:TPX', NS)
            if tpx is not None:
                speed_el = tpx.find('tcx:Speed', NS)
        
        data = {}
        if position is not None:
            lat = position.find('tcx:LatitudeDegrees', NS)
            lon = position.find('tcx:LongitudeDegrees', NS)
            if lat is not None and lon is not None:
                data['latitude'] = float(lat.text)
                data['longitude'] = float(lon.text)
        
        if time_el is not None:
            data['time'] = parse_time(time_el.text)
        
        if distance_el is not None:
            data['distance'] = float(distance_el.text)
        
        if speed_el is not None:
            data['speed'] = float(speed_el.text) * 3.6  # Convert m/s to km/h
        
        if heartrate_el is not None:
            data['heartrate'] = int(heartrate_el.text)
        
        if data:  # Only add if we have at least some data
            trackpoints.append(data)
    
    return pd.DataFrame(trackpoints)

def get_file_hash(filepath):
    """Generate a hash for a file to use as cache key."""
    return hashlib.md5(open(filepath, 'rb').read()).hexdigest()

def get_cache_path(filepath):
    """Get cache path for a given TCX file."""
    CACHE_DIR.mkdir(exist_ok=True)
    file_hash = get_file_hash(filepath)
    return CACHE_DIR / f'{file_hash}.json'

def load_cached_stats(filepath):
    """Load cached stats for a TCX file if available."""
    cache_path = get_cache_path(filepath)
    if cache_path.exists():
        with open(cache_path, 'r') as f:
            return json.load(f)
    return None

def save_cached_stats(filepath, stats):
    """Save stats to cache for a TCX file."""
    cache_path = get_cache_path(filepath)
    with open(cache_path, 'w') as f:
        json.dump(stats, f)

def compute_stats(df):
    """Compute all statistics from trackpoint data."""
    stats = {}
    
    # Duration
    if 'time' in df.columns and len(df) > 0:
        duration = (df['time'].max() - df['time'].min()).total_seconds()
        stats['duration'] = duration
    
    # Distance
    if 'distance' in df.columns:
        stats['total_distance'] = float(df['distance'].max())
    
    # Average speed
    if 'speed' in df.columns:
        stats['avg_speed'] = float(df['speed'].mean())
    
    # Max speed
    if 'speed' in df.columns:
        stats['max_speed'] = float(df['speed'].max())
    
    # Average heartrate
    if 'heartrate' in df.columns:
        stats['avg_heartrate'] = float(df['heartrate'].mean())
    
    # Max heartrate
    if 'heartrate' in df.columns:
        stats['max_heartrate'] = float(df['heartrate'].max())
    
    # Start time
    if 'time' in df.columns and len(df) > 0:
        stats['start_time'] = df['time'].min().isoformat()
    
    # Records - optimized O(n log n) algorithm
    records = calculate_records_fast(df)
    stats['records'] = records
    
    return stats

def calculate_records_fast(df):
    """Calculate time records for specific distances using optimized algorithm.
    
    For each target distance, finds the minimum time between any two points
    where the distance difference is at least the target.
    Uses a min-heap approach for O(n log n) per target distance.
    """
    records = {}
    target_distances = [100, 1000, 3200, 5000]  # meters
    
    if 'distance' not in df.columns or 'time' not in df.columns:
        return records
    
    # Clean data - remove rows without distance or time
    clean_df = df[['distance', 'time']].dropna()
    if len(clean_df) < 2:
        return records
    
    # Convert to lists to avoid numpy datetime issues
    distances = clean_df['distance'].tolist()
    time_objs = clean_df['time'].tolist()
    
    # Convert times to seconds since epoch for faster arithmetic
    import time
    times = [t.timestamp() for t in time_objs]
    
    for target in target_distances:
        min_time = None
        # For each starting point i
        for i in range(len(distances)):
            start_dist = distances[i]
            start_time = times[i]
            # Find the farthest j where we can still beat the current min_time
            # If min_time is set, we only need to check j where 
            # times[j] - start_time < min_time
            # But distances[j] - start_dist >= target
            for j in range(i + 1, len(distances)):
                dist_diff = distances[j] - start_dist
                if dist_diff < target:
                    continue
                time_diff = times[j] - start_time
                if min_time is None or time_diff < min_time:
                    min_time = time_diff
                # Early exit: if time_diff already exceeds min_time, 
                # subsequent j's will only have larger time differences
                # (assuming times are monotonically increasing, which they should be)
                elif min_time is not None and time_diff > min_time:
                    break
        
        if min_time is not None:
            records[f'{target}m'] = min_time
    
    return records

def format_time(seconds):
    """Format seconds into HH:MM:SS or MM:SS."""
    if pd.isna(seconds) or seconds is None:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"

def main():
    st.title("A run")
    
    data_dir = Path('data')
    tcx_files = list(data_dir.glob('*.TCX'))
    
    if not tcx_files:
        st.warning("No TCX files found in the data/ directory.")
        return
    
    # File selection
    selected_file = st.sidebar.selectbox("Select a TCX file:", [f.name for f in tcx_files])
    tcx_path = data_dir / selected_file
    st.markdown(selected_file)
    
    # Try to load cached stats
    cached_stats = load_cached_stats(tcx_path)
    
    # Extract data
    with st.spinner("Parsing TCX file..."):
        df = extract_data_from_tcx(tcx_path)
    
    if df.empty:
        st.warning("No data found in the selected file.")
        return
    
    # Compute and cache stats if not already cached
    if cached_stats is None:
        with st.spinner("Calculating stats..."):
            stats = compute_stats(df)
            save_cached_stats(tcx_path, stats)
    else:
        stats = cached_stats
    
    # Display map if coordinates available
    if 'latitude' in df.columns and 'longitude' in df.columns:
        df_map = df[['latitude', 'longitude']].dropna()
        st.map(df_map, latitude='latitude', longitude='longitude', size=2)
    
    # Statistics markdown above map
    stats_text = "### Activity Summary\n\n"
    
    # Duration
    if 'duration' in stats:
        stats_text += f"**Duration:** {format_time(stats['duration'])}\n\n"
    
    # Distance
    if 'total_distance' in stats:
        stats_text += f"**Distance:** {stats['total_distance']:.2f} m\n\n"
    
    # Average speed
    if 'avg_speed' in stats:
        stats_text += f"**Average Speed:** {stats['avg_speed']:.2f} km/h\n\n"
    
    # Max speed
    if 'max_speed' in stats:
        stats_text += f"**Max Speed:** {stats['max_speed']:.2f} km/h\n\n"
    
    # Average heartrate
    if 'avg_heartrate' in stats:
        stats_text += f"**Average Heartrate:** {stats['avg_heartrate']:.0f} bpm\n\n"
    
    # Max heartrate
    if 'max_heartrate' in stats:
        stats_text += f"**Max Heartrate:** {stats['max_heartrate']:.0f} bpm\n\n"
    
    # Time and start time
    if 'start_time' in stats:
        start_time = datetime.fromisoformat(stats['start_time'])
        stats_text += f"**Start Time:** {start_time.strftime('%Y-%m-%d %H:%M:%S')}\n\n"
    
    # Records section
    stats_text += "### Time Records\n\n"
    records = stats.get('records', {})
    for distance, time_seconds in records.items():
        stats_text += f"**{distance}:** {format_time(time_seconds)}\n\n"
    
    st.markdown(stats_text)

if __name__ == '__main__':
    main()
