import math
import tkinter as tk
from tkinter import Canvas

def mercator_projection(lat, lon, canvas_width, canvas_height):
    map_width = 360.0
    map_height = 180.0

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
    bezier_points = {}
    cubic_bezier_points = {}

    with open(file_path, 'r') as f:
        lines = f.readlines()

    for line in lines:
        tokens = line.split()

        if len(tokens) > 1:
            code = int(tokens[0])

            if code in [100, 101, 102, 110, 120, 130]:
                taxiways.append([])

            elif code in [111, 112, 113, 114, 115, 116]:
                lat, lon = float(tokens[1]), float(tokens[2])
                taxiways[-1].append((lat, lon))

                if code == 112:
                    ctrl_lat, ctrl_lon = float(tokens[3]), float(tokens[4])
                    bezier_points[(lat, lon)] = (ctrl_lat, ctrl_lon)

                if code == 113:
                    cubic_bezier_points[(lat, lon)] = []

                if code == 112 and cubic_bezier_points:
                    last_cubic_key = list(cubic_bezier_points.keys())[-1]
                    ctrl_lat, ctrl_lon = float(tokens[3]), float(tokens[4])
                    cubic_bezier_points[last_cubic_key].append(
                        (ctrl_lat, ctrl_lon))

    return taxiways, bezier_points,  cubic_bezier_points


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
    taxiways, bezier_points, cubic_bezier_points = parse_apt_dat(
        apt_dat_file_path)
    interpolated_taxiways = interpolate_taxiways(
        taxiways, bezier_points, cubic_bezier_points)

    canvas_width, canvas_height = 800, 600

    projected_coords = [
        [mercator_projection(
            lat, lon, canvas_width, canvas_height) for lat, lon in path]
        for path in interpolated_taxiways
    ]

    min_x, min_y = min(p[0] for path in projected_coords for p in path), min(
        p[1] for path in projected_coords for p in path)
    max_x, max_y = max(p[0] for path in projected_coords for p in path), max(
        p[1] for path in projected_coords for p in path)

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

    root.mainloop()


if __name__ == "__main__":
    main()
