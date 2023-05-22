from __future__ import annotations
from iterators import BIterator

import logging

from typing import Optional
from geometry import RowCode

from rich.logging import RichHandler

from classes import (
    AptMetadata,
    Boundary,
    LinearFeature,
    Pavement,
    Runway,
    Sign,
    StartupLocation,
    Windsock,
)
_DEFAULT_BEZIER_RESOLUTION = 16


logging.basicConfig(
    level=logging.INFO,
    format="%(message)s",
    datefmt="[%X]",
    handlers=[RichHandler(show_path=False, omit_repeated_times=False)],
)
logger = logging.getLogger("xplane_apt_convert")
logger.setLevel(logging.INFO)


_BASE_CRS = "EPSG:4326"


VALID_FEATURES = [
    "boundary",
    "runways",
    "startup_locations",
    "windsocks",
    "signs",
    "pavements",
    "linear_features",
]


class ParsedAirport:
    id: str
    metadata: AptMetadata
    boundary: Optional[Boundary]
    runways: list[Runway]
    startup_locations: list[StartupLocation]
    signs: list[Sign]
    windsocks: list[Windsock]
    linear_features: list[LinearFeature]
    pavements: list[Pavement]

    def __init__(
        self,
        airport: RowCode.Airport,
        bezier_resolution: int = _DEFAULT_BEZIER_RESOLUTION,
    ) -> None:
        """A parsed X-Plane airport.

        Args:
            airport (xplane_airports.RowCode.Airport): An X-Plane airport object
                as obtained from `xplane_airports` (https://github.com/X-Plane/xplane_airports).
            bezier_resolution (int): Number of points to use to plot Bezier curves.
                A higher number means more resolution but also larger file sizes on export.
                Default 16.
        """
        self._airport = airport
        self.id = None
        self.metadata = AptMetadata()
        self.boundary = None
        self.runways = []
        self.startup_locations = []
        self.signs = []
        self.windsocks = []
        self.linear_features = []
        self.pavements = []

        self._parse(bezier_resolution=bezier_resolution)

    def _parse(self, bezier_resolution: int) -> None:
        logger.info("Parsing airport.")
        row_iterator = BIterator(self._airport.text)

        for row in row_iterator:
            row_code = row.row_code

            if row_code == RowCode.AIRPORT_HEADER:
                self.id = row.tokens[4]

            if row_code == RowCode.METADATA:
                self.metadata.add_from_row(row)

            elif row_code == RowCode.BOUNDARY:
                logger.debug("Parsing boundary row.")

                boundary = Boundary.from_row_iterator(
                    row, row_iterator, bezier_resolution)

                if boundary is not None:
                    self.boundary = boundary

            elif row_code == RowCode.LAND_RUNWAY:
                logger.debug("Parsing runway row.")

                runway = Runway.from_line(line=row)

                if runway is not None:
                    self.runways.append(runway)

            elif row_code == RowCode.START_LOCATION_NEW:
                logger.debug("Parsing startup location row.")

                startup_location = StartupLocation.from_line(row)

                if startup_location is not None:
                    self.startup_locations.append(startup_location)

                # TODO: process RowCode.START_LOCATION_EXT (startup location metadata)

            elif row_code == RowCode.WINDSOCK:
                logger.debug("Parsing sign row.")

                windsock = Windsock.from_line(row)

                if windsock is not None:
                    self.windsocks.append(windsock)

            elif row_code == RowCode.TAXI_SIGN:
                logger.debug("Parsing sign row.")

                sign = Sign.from_line(row)

                if sign is not None:
                    self.signs.append(sign)

            elif row_code == RowCode.TAXIWAY:
                logger.debug("Parsing pavement row.")

                pavement = Pavement.from_row_iterator(
                    row, row_iterator, bezier_resolution)

                if pavement is not None:
                    self.pavements.append(pavement)

            elif row_code == RowCode.FREE_CHAIN:
                logger.debug("Parsing linear feature row.")

                for line in LinearFeature.from_row_iterator(row, row_iterator, bezier_resolution):
                    if line is not None:
                        self.linear_features.append(line)
