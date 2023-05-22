import math


def latlon_to_xy(lat, lon, ref_lat, ref_lon):
    R = 6371000  # Earth's radius in meters
    x = (lon - ref_lon) * R * math.cos(math.radians(ref_lat))
    y = (lat - ref_lat) * R
    return x, y
