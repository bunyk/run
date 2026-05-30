import webbrowser
from pathlib import Path
import xml.etree.ElementTree as ET

from folium import Map
from folium.plugins import HeatMap

HEATMAP_GRAD = {
    0.0: '#000004',
    0.1: '#160b39',
    0.2: '#420a68',
    0.3: '#6a176e',
    0.4: '#932667',
    0.5: '#bc3754',
    0.6: '#dd513a',
    0.7: '#f37819',
    0.8: '#fca50a',
    0.9: '#f6d746',
    1.0: '#fcffa4',
}
NS = {'tcx': 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2'}

def main():
    heatmap_data = []

    for tcx_file in Path('data').glob('*.tcx'):
        print('Reading {}'.format(tcx_file))

        for p in extract_points_from_tcx(tcx_file):
            heatmap_data.append(p)

    print("Extracted {} points".format(len(heatmap_data)))

    fmap = Map(tiles = 'CartoDB dark_matter',
               prefer_canvas = True,
               max_zoom = 16)

    HeatMap(
        heatmap_data,
        radius = 4,
        blur = 3,
        gradient = HEATMAP_GRAD,
        min_opacity = 0.3,
    ).add_to(fmap)

    fmap.fit_bounds(fmap.get_bounds())

    fmap.save('data/heatmap.html')

    webbrowser.open('data/heatmap.html', new = 2, autoraise = True)

def extract_points_from_tcx(filepath):
    tree = ET.parse(filepath)
    root = tree.getroot()
    
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
                yield [float(lat.text), float(lon.text)]


if __name__ == '__main__':
    main()
