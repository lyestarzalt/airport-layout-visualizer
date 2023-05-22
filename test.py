import tkinter as tk
from base import ParsedAirport
from xplane_airports.AptDat import AptDat
from pyproj import Transformer
import json

class AirportVisualizer:
    def __init__(self, canvas_width=1024, canvas_height=768):
        self.root = tk.Tk()
        self.root.title("Airport Visualization")

        self.canvas = tk.Canvas(
            self.root, width=canvas_width, height=canvas_height)
        self.canvas.pack()

        def on_mousewheel(event):
            x, y = self.canvas.canvasx(event.x), self.canvas.canvasy(event.y)
            zoom = 1.001 ** event.delta

            self.canvas.scale("all", x, y, zoom, zoom)
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))

        self.canvas.bind("<MouseWheel>", on_mousewheel)

    def transform_coordinates(self,coordinates, transformer):
        transformed_coordinates = []
        for path in coordinates:
            transformed_path = [transformer.transform(
                lat, lon) for lat, lon in path]
            transformed_coordinates.append(transformed_path)
        return transformed_coordinates
    
    def draw_taxiways(self, airport):
        pavements = airport.pavements
        coordinates = [pavement.coordinates[0] for pavement in pavements]
        transformer = Transformer.from_proj(
            "EPSG:4326", "EPSG:3857", always_xy=True)
        transformed_coordinates = self.transform_coordinates(
            coordinates, transformer)

        for path in transformed_coordinates:
            points = [coord for coords in path for coord in coords]
            self.canvas.create_polygon(points, fill="", outline="blue")
            self.canvas.create_line(path[-1], path[0], fill="blue")

    def show(self):
        self.root.mainloop()







with open('apt.dat', 'r') as file:
    file_content = file.read()

# Parse the "apt.dat" file content
apt = AptDat.from_file_text(file_content)
apt2 = apt.search_by_id('DAAG')

p_apt = ParsedAirport(apt2, bezier_resolution=20)
print(p_apt.runways[0])

# Initialize the AirportVisualizer and draw the transformed pavement coordinates
visualizer = AirportVisualizer()
visualizer.draw_taxiways(p_apt)
visualizer.show()
