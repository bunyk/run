from datetime import datetime


def format_time(seconds):
    """Format seconds into HH:MM:SS or MM:SS."""
    if not seconds or seconds == 0:
        return "N/A"
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours:02d}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def format_pace(seconds_per_km):
    """Format pace in seconds/km to MM:SS/km."""
    if not seconds_per_km or seconds_per_km == 0:
        return "N/A"
    minutes = int(seconds_per_km // 60)
    secs = int(seconds_per_km % 60)
    return f"{minutes:02d}:{secs:02d}/km"
