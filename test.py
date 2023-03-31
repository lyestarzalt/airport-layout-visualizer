import math
import tkinter as tk
from tkinter import Canvas
from math import radians, sin, cos


def mercator_projection(lat, lon, canvas_width, canvas_height):
    map_width = 360.0
    map_height = 180.0
    lat = max(min(lat, 89.9), -89.9)
    x = (lon + 180.0) * (canvas_width / map_width)
    y = (canvas_height / map_height) * (1 - math.log(math.tan(math.radians(lat)) + 1 /
                                                     math.cos(math.radians(lat))) / math.pi) / 2 * map_height

    return x, y


def normalize_coordinates(x, y, canvas_width, canvas_height, min_x, min_y, max_x, max_y):
    normalized_x = (x - min_x) / (max_x - min_x) * canvas_width
    normalized_y = (y - min_y) / (max_y - min_y) * canvas_height
    return normalized_x, canvas_height - normalized_y


def parse_apt_dat(file_path):
    taxiways = []
    current_path = []
    bezier_points = {}
    cubic_bezier_points = {}
    in_taxiway = False
    runways = []

    with open(file_path, "r") as f:
        for line in f:
            tokens = line.strip().split()
            try:
                code = int(tokens[0])
            except Exception:
                continue
            if code == 100:  # Runway

                width = float(tokens[1])
                lat1, lon1 = float(tokens[9]), float(tokens[10])
                lat2, lon2 = float(tokens[18]), float(tokens[19])
                runways.append([(lat1, lon1), (lat2, lon2), width])
            if code == 110:  # Pavement (taxiway or ramp) header
                if in_taxiway:
                    taxiways.append(current_path)
                    current_path = []
                else:
                    in_taxiway = True
                continue

            if not in_taxiway:
                continue

            if in_taxiway and code == 111:  # Node
                lat, lon = float(tokens[1]), float(tokens[2])
                current_path.append((lat, lon))

                if len(tokens) > 3 and code != 111:  # Node with Bezier control point
                    ctrl_lat, ctrl_lon = float(tokens[3]), float(tokens[4])
                    bezier_points[(lat, lon)] = (ctrl_lat, ctrl_lon)
            if code == 113:  # Node with implicit close of loop
                current_path.append(current_path[0])
                taxiways.append(current_path)
                current_path = []
                in_taxiway = False
            if code in {112, 114}:  # Node with Bezier control point
                lat, lon = float(tokens[1]), float(tokens[2])
                current_path.append((lat, lon))
                cubic_bezier_points[(lat, lon)] = []
                if code in {112, 114}:  # Node with Bezier control point
                    ctrl_lat, ctrl_lon = float(tokens[3]), float(tokens[4])
                    cubic_bezier_points[(lat, lon)].append(
                        (ctrl_lat, ctrl_lon))

    if in_taxiway:
        taxiways.append(current_path)

    return taxiways, bezier_points, cubic_bezier_points, runways


def bezier_interpolation(t, p0, p1, p2):
    return (
        (1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t ** 2 * p2[0],
        (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t ** 2 * p2[1]
    )


def bezier_cubic_interpolation(t, p0, p1, p2, p3):
    return (
        (1 - t) ** 3 * p0[0] + 3 * (1 - t) ** 2 * t *
        p1[0] + 3 * (1 - t) * t ** 2 * p2[0] + t ** 3 * p3[0],
        (1 - t) ** 3 * p0[1] + 3 * (1 - t) ** 2 * t *
        p1[1] + 3 * (1 - t) * t ** 2 * p2[1] + t ** 3 * p3[1]
    )


def calculate_runway_corners(p1, p2, width, scale):
    lat1, lon1 = p1
    lat2, lon2 = p2

    d = haversine(lat1, lon1, lat2, lon2)
    dx = (lat2 - lat1) / d
    dy = (lon2 - lon1) / d

    width_rad = width / (6371 * 1000)  # Convert width to radians

    wx = width_rad * dy / 2 * scale
    wy = width_rad * dx / 2 * scale

    corners = [
        (lat1 - wx, lon1 + wy),
        (lat1 + wx, lon1 - wy),
        (lat2 + wx, lon2 - wy),
        (lat2 - wx, lon2 + wy)
    ]

    return corners


def haversine(lat1, lon1, lat2, lon2):
    R = 6371  # Earth's radius in km
    d_lat = radians(lat2 - lat1)
    d_lon = radians(lon2 - lon1)
    a = sin(d_lat / 2) ** 2 + cos(radians(lat1)) * \
        cos(radians(lat2)) * sin(d_lon / 2) ** 2
    return 2 * R * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def interpolate_taxiways(taxiways, bezier_points, cubic_bezier_points, num_points=100):
    interpolated_taxiways = []

    for taxiway in taxiways:
        interpolated_taxiway = []

        n = len(taxiway)
        i = 0
        while i < n:
            p1 = taxiway[i]
            interpolated_taxiway.append(p1)

            if p1 in bezier_points:
                ctrl_point1 = bezier_points[p1]
                p2 = taxiway[(i + 1) % n]

                cubic_interpolation_flag = False
                if p2 in cubic_bezier_points:
                    # Cubic Bezier
                    if len(cubic_bezier_points[p2]) >= 2:
                        ctrl_point2, p3 = cubic_bezier_points[p2][0], cubic_bezier_points[p2][1]
                        cubic_interpolation_flag = True

                if cubic_interpolation_flag:
                    for t in range(1, num_points):
                        interpolated_taxiway.append(bezier_cubic_interpolation(
                            t / num_points, p1, ctrl_point1, ctrl_point2, p3))

                    i += 1
                else:
                    # Quadratic Bezier
                    for t in range(1, num_points):
                        interpolated_taxiway.append(bezier_interpolation(
                            t / num_points, p1, ctrl_point1, p2))

            i += 1

        interpolated_taxiways.append(interpolated_taxiway)

    return interpolated_taxiways


def main():
    apt_dat_file_path = "apt.dat"
    taxiways, bezier_points, cubic_bezier_points, runways = parse_apt_dat(
        apt_dat_file_path)
    interpolated_taxiways = interpolate_taxiways(
        taxiways, bezier_points, cubic_bezier_points)

    canvas_width, canvas_height = 800, 600

    projected_coords = [
        [mercator_projection(
            lat, lon, canvas_width, canvas_height) for lat, lon in path]
        for path in interpolated_taxiways
    ]

    projected_runways = [
        [mercator_projection(lat, lon, canvas_width, canvas_height)
         for lat, lon in runway[:2]]
        for runway in runways
    ]

    min_x, min_y = min(min(p[0] for path in projected_coords for p in path), min(p[0] for runway in projected_runways for p in runway)), \
        min(min(p[1] for path in projected_coords for p in path), min(p[1]
            for runway in projected_runways for p in runway))

    max_x, max_y = max(max(p[0] for path in projected_coords for p in path), max(p[0] for runway in projected_runways for p in runway)), \
        max(max(p[1] for path in projected_coords for p in path), max(p[1]
            for runway in projected_runways for p in runway))

    root = tk.Tk()
    root.title("Latitude and Longitude Path")
    canvas = tk.Canvas(root, width=canvas_width, height=canvas_height)
    canvas.pack()

    def on_mousewheel(event):
        x, y = canvas.canvasx(event.x), canvas.canvasy(event.y)
        zoom = 1.001 ** event.delta

        canvas.scale("all", x, y, zoom, zoom)

        canvas.configure(scrollregion=canvas.bbox("all"))

    canvas.bind("<MouseWheel>", on_mousewheel)

    for path in projected_coords:
        normalized_path = [
            normalize_coordinates(x, y, canvas_width,
                                  canvas_height, min_x, min_y, max_x, max_y)
            for x, y in path
        ]

        for i in range(len(normalized_path) - 1):
            x1, y1 = normalized_path[i]
            x2, y2 = normalized_path[i + 1]
            canvas.create_line(x1, y1, x2, y2, fill="blue", width=1)
    scale_x = canvas_width / (max_x - min_x)
    scale_y = canvas_height / (max_y - min_y)
    scale = min(scale_x, scale_y)
    for runway, projected_runway in zip(runways, projected_runways):
        width = runway[2]
        max_taxiway_distance = max(math.sqrt((x2 - x1) ** 2 + (y2 - y1) ** 2)
                                for path in projected_coords for (x1, y1), (x2, y2) in zip(path[:-1], path[1:]))

        geo_corners = calculate_runway_corners(
            runway[0], runway[1], width, scale)
        projected_corners = [mercator_projection(
            lat, lon, canvas_width, canvas_height) for lat, lon in geo_corners]
        normalized_corners = [normalize_coordinates(
            x, y, canvas_width, canvas_height, min_x, min_y, max_x, max_y) for x, y in projected_corners]

        canvas.create_polygon(normalized_corners, fill="red",
                            outline="black", width=1)


    root.mainloop()


if __name__ == "__main__":
    main()
