import xml.etree.ElementTree as ET
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
        """Return duration in seconds."""
        times = self._get_times()
        if len(times) >= 2:
            return (max(times) - min(times)).total_seconds()
        return 0

    @property
    def total_distance(self):
        """Return total distance in meters."""
        max_dist = 0
        for tp in self.trackpoints:
            dist = tp.find('tcx:DistanceMeters', NS)
            if dist is not None:
                max_dist = max(max_dist, float(dist.text))
        return max_dist

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

    def _get_speeds_from_xml(self):
        """Try to get speeds from XML (Speed or TPX elements)."""
        speeds = []
        for tp in self.trackpoints:
            speed = tp.find('tcx:Speed', NS)
            if speed is not None:
                speeds.append(float(speed.text) * 3.6)
            else:
                tpx = tp.find('.//tcx:TPX', NS)
                if tpx is not None:
                    speed = tpx.find('tcx:Speed', NS)
                    if speed is not None:
                        speeds.append(float(speed.text) * 3.6)
        return speeds

    def _calculate_speeds_from_distance(self):
        """Calculate speeds from distance/time differences."""
        distances = self._get_distances()
        times = self._get_times()
        if len(distances) < 2 or len(times) < 2:
            return []
        speeds = []
        for i in range(1, len(distances)):
            dist_diff = distances[i] - distances[i-1]
            time_diff = (times[i] - times[i-1]).total_seconds()
            if time_diff > 0:
                # speed in m/s * 3.6 = km/h
                speeds.append((dist_diff / time_diff) * 3.6)
        return speeds

    @property
    def avg_speed(self):
        """Return average speed in km/h."""
        # Try to get speeds from XML first
        speeds = self._get_speeds_from_xml()
        if speeds:
            return sum(speeds) / len(speeds)
        # Fall back to calculating from distance/time
        speeds = self._calculate_speeds_from_distance()
        if speeds:
            return sum(speeds) / len(speeds)
        return 0

    def top_speed(self, interval_seconds=60):
        """Return top speed over a given time interval in km/h."""
        # Try to get speeds from XML first
        xml_speeds = self._get_speeds_from_xml()
        times = self._get_times()

        if xml_speeds and len(xml_speeds) == len(times):
            speeds = xml_speeds
            time_speed_pairs = list(zip(times, speeds))
        else:
            # Fall back to calculating from distance/time
            # Calculated speeds are between consecutive points, so we use the midpoint time
            distances = self._get_distances()
            if len(distances) < 2 or len(times) < 2:
                return 0
            time_speed_pairs = []
            for i in range(1, len(distances)):
                dist_diff = distances[i] - distances[i-1]
                time_diff = (times[i] - times[i-1]).total_seconds()
                if time_diff > 0:
                    speed = (dist_diff / time_diff) * 3.6
                    # Use midpoint time for this speed
                    mid_time = times[i-1] + (times[i] - times[i-1]) / 2
                    time_speed_pairs.append((mid_time, speed))

        if not time_speed_pairs:
            return 0

        # Extract times and speeds from pairs
        times = [p[0] for p in time_speed_pairs]
        speeds = [p[1] for p in time_speed_pairs]

        max_speed = 0
        for i in range(len(times)):
            current_time = times[i]
            current_speed = speeds[i]
            # Check all points within the interval
            for j in range(i, len(times)):
                if (times[j] - current_time).total_seconds() <= interval_seconds:
                    max_speed = max(max_speed, speeds[j])
                else:
                    break

        return max_speed
