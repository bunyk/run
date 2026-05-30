import sqlite3
import os
from datetime import datetime
from pathlib import Path

from tcx import TCX


class ActivityDB:
    """SQLite database for storing activity data."""

    def __init__(self, db_path='data/activities.db'):
        """Open or create SQLite database."""
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self.conn = sqlite3.connect(db_path)
        self._create_tables()

    def _create_tables(self):
        """Create activities table if it doesn't exist."""
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS activities (
                filename TEXT PRIMARY KEY,
                type TEXT,
                start_time TEXT,
                duration REAL,
                distance REAL,
                best_100 REAL,
                best_1k REAL,
                best_3200 REAL,
                best_5k REAL,
                best_10k REAL
            )
        ''')
        self.conn.commit()

    def insert_activity(self, filename, type, start_time, duration, distance, 
                       best_100=None, best_1k=None, best_3200=None, best_5k=None, best_10k=None):
        """Insert an activity into the database."""
        if isinstance(start_time, datetime):
            start_time = start_time.isoformat()
        self.conn.execute(
            '''INSERT OR REPLACE INTO activities 
               (filename, type, start_time, duration, distance, best_100, best_1k, best_3200, best_5k, best_10k) 
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (filename, type, start_time, duration, distance, 
             best_100, best_1k, best_3200, best_5k, best_10k)
        )
        self.conn.commit()

    def get_types(self):
        """Return list of distinct activity types."""
        cursor = self.conn.execute('SELECT DISTINCT type FROM activities')
        return [row[0] for row in cursor]
    
    def get_activities_count(self):
        """Return total count of activities in the database."""
        cursor = self.conn.execute('SELECT COUNT(*) FROM activities')
        return cursor.fetchone()[0]
    
    def get_total_duration(self):
        """Return total duration of all activities in seconds."""
        cursor = self.conn.execute('SELECT SUM(duration) FROM activities')
        result = cursor.fetchone()[0]
        return result if result is not None else 0

    def get_total_distance(self):
        """Return total distance of all activities in meters."""
        cursor = self.conn.execute('SELECT SUM(distance) FROM activities')
        result = cursor.fetchone()[0]
        return result if result is not None else 0

    def get_activities(self):
        """Return list of activities filtered by type."""
        cursor = self.conn.execute(
            '''SELECT filename, type, start_time, duration, distance, 
                      best_100, best_1k, best_3200, best_5k, best_10k 
               FROM activities''',
        )
        activities = []
        for row in cursor:
            activities.append({
                'filename': row[0],
                'type': row[1],
                'start_time': row[2],
                'duration': row[3],
                'distance': row[4],
                'best_100': row[5],
                'best_1k': row[6],
                'best_3200': row[7],
                'best_5k': row[8],
                'best_10k': row[9]
            })
        return activities

    def close(self):
        """Close the database connection."""
        self.conn.close()


    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

def reindex():
    """Browse all TCX files in data directory and add unprocessed ones to DB.
    
    For each TCX file not already in the database:
    - Parses it using TCX class
    - Extracts attributes (type, start_time, duration, distance)
    - Calculates best times for standard distances
    - Inserts into database
    
    Returns count of files processed.
    """
    data_path = Path('data')
    tcx_files = list(data_path.glob('*.tcx'))
    
    with ActivityDB() as db:
        # Get existing filenames from DB
        cursor = db.conn.execute('SELECT filename FROM activities')
        existing = {row[0] for row in cursor}
        
        processed_count = 0
        for tcx_file in tcx_files:
            filename = tcx_file.name
            if filename not in existing:
                # Parse TCX file
                tcx = TCX(str(tcx_file))
                
                # Get best times for standard distances
                best_100 = tcx.best_time_for_distance(100)
                best_1k = tcx.best_time_for_distance(1000)
                best_3200 = tcx.best_time_for_distance(3200)
                best_5k = tcx.best_time_for_distance(5000)
                best_10k = tcx.best_time_for_distance(10000)
                
                # Get start time from first trackpoint
                times = tcx._get_times()
                start_time = times[0] if times else None
                
                print(filename, type, start_time, tcx.duration, tcx.distance, best_100, best_1k, best_3200, best_5k, best_10k)
                # Insert into DB
                db.insert_activity(
                    filename=filename,
                    type=tcx.activity_type or 'Unknown',
                    start_time=start_time,
                    duration=tcx.duration,
                    distance=tcx.distance,
                    best_100=best_100 if best_100 > 0 else None,
                    best_1k=best_1k if best_1k > 0 else None,
                    best_3200=best_3200 if best_3200 > 0 else None,
                    best_5k=best_5k if best_5k > 0 else None,
                    best_10k=best_10k if best_10k > 0 else None
                )
                processed_count += 1
        
        db.conn.commit()
        return processed_count
