import xml.etree.ElementTree as ET
import pandas as pd
from datetime import datetime

NS = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}


class TCX:
    """Class to handle TCX file parsing and provide activity data."""

    def __init__(self, filepath):
        """Load and parse a TCX file."""
        self.filepath = filepath
        self.tree = ET.parse(filepath)
        self.root = self.tree.getroot()
        self._trackpoints = None
        self._activity_type = None

    @staticmethod
    def parse_time(time_str):
        """Parse ISO 8601 datetime string to datetime object."""
        return datetime.fromisoformat(time_str.replace('Z', '+00:00'))

    @property
    def activity_type(self):
        """Get the activity type from the TCX file."""
        if self._activity_type is None:
            activity = self.root.find('.//tcx:Activity', NS)
            if activity is not None:
                sport = activity.get('Sport')
                if sport:
                    self._activity_type = sport
        return self._activity_type

    @property
    def trackpoints(self):
        """Lazy-load and return all trackpoints."""
        if self._trackpoints is None:
            self._trackpoints = list(self.root.findall('.//tcx:Trackpoint', NS))
        return self._trackpoints

    @property
    def coordinates(self):
        """Return sequence of (latitude, longitude) tuples."""
        coords = []
        for tp in self.trackpoints:
            pos = tp.find('tcx:Position', NS)
            if pos is not None:
                lat = pos.find('tcx:LatitudeDegrees', NS)
                lon = pos.find('tcx:LongitudeDegrees', NS)
                if lat is not None and lon is not None:
                    coords.append((float(lat.text), float(lon.text)))
        return coords

    @property
    def duration(self):
        """Return total duration in seconds (sum of lap times)."""
        total = 0
        for lap in self.root.findall('.//tcx:Lap', NS):
            total_time = lap.find('tcx:TotalTimeSeconds', NS)
            if total_time is not None:
                total += float(total_time.text)
        return total

    @property
    def distance(self):
        """Return total distance in meters (sum of lap distances)."""
        total = 0
        for lap in self.root.findall('.//tcx:Lap', NS):
            distance = lap.find('tcx:DistanceMeters', NS)
            if distance is not None:
                total += float(distance.text)
        return total

    @property
    def laps(self):
        """Return list of laps with their stats (time, distance)."""
        laps = []
        for lap in self.root.findall('.//tcx:Lap', NS):
            lap_data = {}
            
            # Get total time/duration
            total_time = lap.find('tcx:TotalTimeSeconds', NS)
            if total_time is not None:
                lap_data['time'] = float(total_time.text)
            
            # Get distance
            distance = lap.find('tcx:DistanceMeters', NS)
            if distance is not None:
                lap_data['distance'] = float(distance.text)
            
            laps.append(lap_data)
        return laps

    @property
    def avg_speed(self):
        """Return average speed in km/h."""
        if self.duration > 0:
            return self.distance / 1000 / (self.duration / 3600)
        return 0

    def _get_times(self):
        """Helper to get all timestamps."""
        times = []
        for tp in self.trackpoints:
            time_el = tp.find('tcx:Time', NS)
            if time_el is not None:
                times.append(self.parse_time(time_el.text))
        return times

    def _get_distances(self):
        """Helper to get all distances in meters."""
        distances = []
        for tp in self.trackpoints:
            dist = tp.find('tcx:DistanceMeters', NS)
            if dist is not None:
                distances.append(float(dist.text))
        return distances

    def best_time_for_distance(self, target_distance_m):
        """Return best (minimum) time in seconds to cover at least target_distance_m.
        
        Searches through trackpoints to find the fastest segment covering the given distance.
        Returns 0 if the target distance exceeds the total activity distance.
        """
        if target_distance_m <= 0:
            return 0
        
        # Get all distances and times
        distances = self._get_distances()
        times = self._get_times()
        
        if len(distances) < 2 or len(times) < 2:
            return 0
        
        max_distance = max(distances) if distances else 0
        min_distance = min(distances) if distances else 0
        max_possible_distance = max_distance - min_distance
        
        # If target exceeds total possible distance, return 0
        if target_distance_m > max_possible_distance:
            return 0
        
        best_time = float('inf')
        
        # Use sliding window to find segments covering at least target_distance_m
        for i in range(len(distances)):
            for j in range(i + 1, len(distances)):
                dist_diff = distances[j] - distances[i]
                if dist_diff >= target_distance_m:
                    time_diff = (times[j] - times[i]).total_seconds()
                    best_time = min(best_time, time_diff)
                    # Early exit for this i - any larger j will be slower
                    break
        
        return best_time if best_time != float('inf') else 0

    def get_trackpoint_data(self):
        """Return pandas DataFrame with Speed, Cadence, HeartRate per trackpoint.
        
        Speed is calculated from DistanceMeters and Time differences if not present in XML.
        """
        # Pre-fetch all times and distances for speed calculation
        all_times = []
        all_distances = []
        for tp in self.trackpoints:
            time_el = tp.find('tcx:Time', NS)
            all_times.append(self.parse_time(time_el.text) if time_el is not None else None)
            
            dist_el = tp.find('tcx:DistanceMeters', NS)
            all_distances.append(float(dist_el.text) if dist_el is not None else None)
        
        data = []
        prev_time = None
        prev_dist = None
        
        for i, tp in enumerate(self.trackpoints):
            row = {}
            
            # Get time
            time_el = tp.find('tcx:Time', NS)
            if time_el is not None:
                row['Time'] = self.parse_time(time_el.text)
            
            # Get or calculate Speed (km/h)
            speed = tp.find('tcx:Speed', NS)
            if speed is not None:
                row['Speed'] = float(speed.text) * 3.6
            else:
                tpx = tp.find('.//tcx:TPX', NS)
                if tpx is not None:
                    speed = tpx.find('tcx:Speed', NS)
                    if speed is not None:
                        row['Speed'] = float(speed.text) * 3.6
                # Calculate from distance/time difference
                if i > 0 and prev_time is not None and prev_dist is not None:
                    current_time = all_times[i]
                    current_dist = all_distances[i]
                    if current_time is not None and current_dist is not None:
                        time_diff = (current_time - prev_time).total_seconds()
                        dist_diff = current_dist - prev_dist
                        if time_diff > 0:
                            row['Speed'] = (dist_diff / time_diff) * 3.6
            
            # Get Cadence (RPM)
            cadence = tp.find('tcx:Cadence', NS)
            if cadence is not None:
                row['Cadence'] = float(cadence.text)
            else:
                if tpx is not None:
                    cadence = tpx.find('tcx:Cadence', NS)
                    if cadence is not None:
                        row['Cadence'] = float(cadence.text)
            
            # Get HeartRate (bpm)
            hr = tp.find('.//tcx:HeartRateBpm/tcx:Value', NS)
            if hr is not None:
                row['HeartRate'] = float(hr.text)
            else:
                if tpx is not None:
                    hr = tpx.find('tcx:HeartRate', NS)
                    if hr is not None:
                        row['HeartRate'] = float(hr.text)
            
            data.append(row)
            
            # Update previous for next iteration
            prev_time = all_times[i]
            prev_dist = all_distances[i]
        
        return pd.DataFrame(data)
