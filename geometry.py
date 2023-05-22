import numpy as np
from enum import IntEnum


class RowCode(IntEnum):
    AIRPORT_HEADER = 1
    _RUNWAY_OLD = 10  # Legacy runway/taxiway record from X-Plane 8.10 and earlier
    TOWER_LOCATION = 14
    STARTUP_LOCATION = 15
    SEAPORT_HEADER = 16
    HELIPORT_HEADER = 17
    BEACON = 18
    WINDSOCK = 19
    FREQUENCY_AWOS = 50
    FREQUENCY_CTAF = 51
    FREQUENCY_DELIVERY = 52
    FREQUENCY_GROUND = 53
    FREQUENCY_TOWER = 54
    FREQUENCY_APPROACH = 55
    FREQUENCY_CENTER = 56
    FREQUENCY_UNICOM = 57
    FILE_END = 99
    # These records were new with X-Plane 8.50
    TAXI_SIGN = 20
    PAPI_LIGHTS = 21

    LAND_RUNWAY = 100  # These replace the old type 10 record.
    WATER_RUNWAY = 101
    HELIPAD = 102
    TAXIWAY = 110
    FREE_CHAIN = 120
    BOUNDARY = 130

    LINE_SEGMENT = 111
    LINE_CURVE = 112
    RING_SEGMENT = 113
    RING_CURVE = 114
    END_SEGMENT = 115
    END_CURVE = 116

    # These records were new with X-Plane 10
    FLOW_DEFINITION = 1000  # 1000 <traffic flow name, must be unique to the ICAO airport>
    FLOW_WIND = 1001  # 1001 <metar icao> <wind dir min> <wind dir max> <wind max speed>
    FLOW_CEILING = 1002  # 1002 <metar icao> <ceiling minimum>
    FLOW_VISIBILITY = 1003  # 1003 <metar icao> <vis minimum>
    FLOW_TIME = 1004  # 1004 <zulu time start> <zulu time end>

    CHANNEL_AWOS = 1050  # 8.33kHz 6-digit COM channels replacing the 50..57 records
    CHANNEL_CTAF = 1051
    CHANNEL_DELIVERY = 1052
    CHANNEL_GROUND = 1053
    CHANNEL_TOWER = 1054
    CHANNEL_APPROACH = 1055
    CHANNEL_CENTER = 1056
    CHANNEL_UNICOM = 1057

    FLOW_RUNWAY_RULE = 1100
    FLOW_PATTERN = 1101
    FLOW_RUNWAY_RULE_CHANNEL = 1110

    TAXI_ROUTE_HEADER = 1200
    TAXI_ROUTE_NODE = 1201
    TAXI_ROUTE_EDGE = 1202
    TAXI_ROUTE_SHAPE = 1203
    TAXI_ROUTE_HOLD = 1204
    TAXI_ROUTE_ROAD = 1206

    START_LOCATION_NEW = 1300  # Replaces 15 record
    START_LOCATION_EXT = 1301
    METADATA = 1302

    TRUCK_PARKING = 1400
    TRUCK_DESTINATION = 1401

    def __int__(self):
        return self.value

    def __str__(self):
        return str(self.value)


_DEFAULT_BEZIER_RESOLUTION = 16


def quadratic_bezier(t, p0, p1, p2):
    return (1 - t) * (1 - t) * p0 + 2 * (1 - t) * t * p1 + t * t * p2


def cubic_bezier(t, p0, p1, p2, p3):
    return (
        (1 - t) * (1 - t) * (1 - t) * p0
        + 3 * (1 - t) * (1 - t) * t * p1
        + 3 * (1 - t) * t * t * p2
        + t * t * t * p3
    )


def _calculate_bezier(p0, p1, p2, p3=None, resolution=_DEFAULT_BEZIER_RESOLUTION):
    if p3 is None:
        return [
            (quadratic_bezier(t, p0[0], p1[0], p2[0]),
             quadratic_bezier(t, p0[1], p1[1], p2[1]))
            for t in np.linspace(0.0, 1.0, resolution)
        ]
    else:
        return [
            (cubic_bezier(t, p0[0], p1[0], p2[0], p3[0]),
             cubic_bezier(t, p0[1], p1[1], p2[1], p3[1]))
            for t in np.linspace(0.0, 1.0, resolution)
        ]


def get_paths(row_iterator, bezier_resolution, mode="line"):
    # https://forums.x-plane.org/index.php?/forums/topic/66713-understanding-the-logic-of-bezier-control-points-in-aptdat/

    assert mode == "line" or mode == "polygon"

    coordinates = []
    properties = {}

    def _start_segment():
        nonlocal coordinates, properties
        coordinates = []
        properties = {}

    def _finish_segment():
        nonlocal coordinates, properties
        if len(coordinates) > 1:
            # simplify line. remove consecutive duplicates
            prev_c = None
            fixed_coordinates = []
            for c in coordinates:
                if prev_c is not None and tuple(c) == tuple(prev_c):
                    continue

                fixed_coordinates.append(c)

                prev_c = c

            coordinates_list.append(fixed_coordinates)
            properties_list.append(properties)

    def _process_row(is_bezier, tokens):
        nonlocal in_bezier, temp_bezier_nodes, coordinates, properties
        lat, lon = float(tokens[1]), float(tokens[2])

        if not is_bezier:
            if in_bezier:
                temp_bezier_nodes.append((lon, lat))
                coordinates.extend(
                    _calculate_bezier(*temp_bezier_nodes)
                )  # TODO: pass resolution argument
                temp_bezier_nodes = []
            else:
                coordinates.append((lon, lat))

            in_bezier = False

            painted_line_type = int(tokens[3]) if len(tokens) > 3 else None
            lighting_line_type = int(tokens[4]) if len(tokens) > 4 else None

            if mode == "line" and (
                (
                    painted_line_type is not None
                    and properties.get("painted_line_type") is not None
                    and painted_line_type != properties["painted_line_type"]
                )
                or (
                    lighting_line_type is not None
                    and properties.get("lighting_line_type") is not None
                    and lighting_line_type != properties["lighting_line_type"]
                )
            ):
                if row_iterator.has_next():
                    _finish_segment()
                    _start_segment()
                    row_iterator.unnext()  # reuse row for the new segment
            else:
                if painted_line_type is not None:
                    properties["painted_line_type"] = painted_line_type

                if lighting_line_type is not None:
                    properties["lighting_line_type"] = lighting_line_type

        else:
            bzp_lat, bzp_lon = float(tokens[3]), float(tokens[4])

            if in_bezier:
                diff_lat = bzp_lat - lat
                diff_lon = bzp_lon - lon
                mirr_lat = lat - diff_lat
                mirr_lon = lon - diff_lon

                temp_bezier_nodes.append((mirr_lon, mirr_lat))
                temp_bezier_nodes.append((lon, lat))
                coordinates.extend(
                    _calculate_bezier(*temp_bezier_nodes,
                                      resolution=bezier_resolution)
                )
                temp_bezier_nodes = []
            else:
                if len(coordinates) != 0:
                    diff_lat = bzp_lat - lat
                    diff_lon = bzp_lon - lon
                    mirr_lat = lat - diff_lat
                    mirr_lon = lon - diff_lon

                    temp_bezier_nodes.append(coordinates[-1])
                    temp_bezier_nodes.append((mirr_lon, mirr_lat))
                    temp_bezier_nodes.append((lon, lat))
                    coordinates.extend(
                        _calculate_bezier(
                            *temp_bezier_nodes, resolution=bezier_resolution
                        )
                    )
                    temp_bezier_nodes = []

            temp_bezier_nodes.append((lon, lat))
            temp_bezier_nodes.append((bzp_lon, bzp_lat))

            # else:
            in_bezier = True

            painted_line_type = int(tokens[5]) if len(tokens) > 5 else None
            lighting_line_type = int(tokens[6]) if len(tokens) > 6 else None

            if mode == "line" and (
                (
                    painted_line_type is not None
                    and properties.get("painted_line_type") is not None
                    and painted_line_type != properties["painted_line_type"]
                )
                or (
                    lighting_line_type is not None
                    and properties.get("lighting_line_type") is not None
                    and lighting_line_type != properties["lighting_line_type"]
                )
            ):
                if row_iterator.has_next():
                    _finish_segment()
                    _start_segment()
                    row_iterator.unnext()  # reuse row for the new segment
            else:
                if painted_line_type is not None:
                    properties["painted_line_type"] = painted_line_type

                if lighting_line_type is not None:
                    properties["lighting_line_type"] = lighting_line_type

    coordinates_list = []
    properties_list = []
    more_segments = True

    while more_segments:
        temp_bezier_nodes = []
        in_bezier = False
        first_row = None
        first_row_is_bezier = None

        _start_segment()

        for row in row_iterator:
            if first_row is None:
                first_row = row
                first_row_is_bezier = row.row_code in [
                    RowCode.LINE_CURVE,
                    RowCode.RING_CURVE,
                    RowCode.END_CURVE,
                ]

            row_code = row.row_code
            tokens = row.tokens

            if row_code == RowCode.LINE_SEGMENT:
                _process_row(False, tokens)
            elif row_code == RowCode.LINE_CURVE:
                _process_row(True, tokens)
            elif row_code == RowCode.RING_SEGMENT:
                _process_row(False, tokens)
                _process_row(first_row_is_bezier, first_row.tokens)
                break
            elif row_code == RowCode.RING_CURVE:
                _process_row(True, tokens)
                _process_row(first_row_is_bezier, first_row.tokens)
                break
            elif row_code == RowCode.END_SEGMENT:
                _process_row(False, tokens)
                break
            elif row_code == RowCode.END_CURVE:
                _process_row(True, tokens)
                break
            else:
                row_iterator.unnext()
                more_segments = False
                break
        else:
            # there is no more rows
            more_segments = False

        _finish_segment()

    assert len(coordinates_list) == len(properties_list)
    return coordinates_list, properties_list
