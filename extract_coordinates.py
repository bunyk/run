#!/usr/bin/env python3
import os
import xml.etree.ElementTree as ET
from pathlib import Path

# Namespace for TCX files
NS = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

def extract_coordinates_from_tcx(filepath):
    """Extract latitude and longitude degrees from a TCX file."""
    tree = ET.parse(filepath)
    root = tree.getroot()
    
    coordinates = []
    
    # Find all Trackpoint elements with Position
    for trackpoint in root.findall('.//tcx:Trackpoint', NS):
        position = trackpoint.find('tcx:Position', NS)
        if position is not None:
            lat = position.find('tcx:LatitudeDegrees', NS)
            lon = position.find('tcx:LongitudeDegrees', NS)
            if lat is not None and lon is not None:
                coordinates.append({
                    'latitude': float(lat.text),
                    'longitude': float(lon.text)
                })
    
    return coordinates

def main():
    data_dir = Path('data')
    all_coordinates = []
    
    for tcx_file in data_dir.glob('*.TCX'):
        coords = extract_coordinates_from_tcx(tcx_file)
        all_coordinates.extend(coords)
        print(f"Found {len(coords)} coordinates in {tcx_file.name}")
    
    print(f"\nTotal coordinates extracted: {len(all_coordinates)}")
    print("\nCoordinates (latitude, longitude):")
    for i, coord in enumerate(all_coordinates, 1):
        print(f"{i}: {coord['latitude']}, {coord['longitude']}")

if __name__ == '__main__':
    main()
