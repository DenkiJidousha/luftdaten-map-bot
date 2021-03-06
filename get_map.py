# conda install -c conda-forge cartopy
import os
from math import sqrt
from statistics import mean

import geotiler
import json
from matplotlib.colors import LinearSegmentedColormap
from PIL import Image, ImageDraw

legend_img = Image.open("legend.png")
print("Loaded legend, %i by %i" % legend_img.size)

# Saved from http://api.luftdaten.info/static/v2/data.json (5min average)
# or http://api.luftdaten.info/static/v2/data.1h.json
# or http://api.luftdaten.info/static/v2/data.24h.json
luftdaten_v2_all_json = "luftdaten_v2_all_2019_02_23_23_41_24hr.json"

with open(luftdaten_v2_all_json) as handle:
    world_data = json.load(handle)
world_data = [_ for _ in world_data if _["sensor"]["sensor_type"]["name"] == "SDS011" and _["location"]["longitude"] and _["location"]["latitude"] and _["sensordatavalues"]]

print("Have %i points for SDS011 world wide" % len(world_data))

# legend=0 off, 1 top left (default), 2 top right, 3 bottom right, 4 bottom left
jobs = [
    dict(
        name="World", latitude=0, longitude=0, zoom=1, size=(500, 500), legend=(0, 285)
    ),
    dict(name="Europe", latitude=53.9, longitude=14.5, zoom=4),
    dict(name="Germany", latitude=51.305, longitude=8.659, zoom=6),
    dict(name="UK", latitude=55.3, longitude=-3.3, zoom=5, legend=(0, 385)),
    dict(name="Scotland", latitude=57.78, longitude=-5, zoom=6),
    dict(name="Aberdeen", latitude=57.155, longitude=-2.14, legend=(0, 385)),
    dict(name="Bristol", latitude=51.463, longitude=-2.61, legend=(0, 385)),
    dict(name="Eastbourne", latitude=50.795, longitude=0.268, legend=(505, 385)),
    dict(name="Sheffield", latitude=53.38, longitude=-1.47),
]

# From the legend CSS:
# linear-gradient(to top,
#                 #00796b 0%,    <--   0ug/m3
#                 #00796b 16%,
#                         20%    <--  25ug/m3
#                 #f9a825 32%,
#                         40%,   <--  50ug/m3
#                 #e65100 48%,
#                         60%,   <--  75ug/m3
#                 #dd2c00 72%,
#                 #dd2c00 80%,   <-- 100ug/m3
#                 #8c0084 100%); <-- 500ug/m3
# Limit line at 50ug/m3
#
# https://github.com/opendata-stuttgart/feinstaub-map/blob/master/src/hexbin-layer.js
# valueDomain: [20, 40, 60, 100, 500],
# colorRange: ['#00796B', '#F9A825', '#E65100', '#DD2C00', '#960084'],

alpha = 125 / 256
cdict = {
    "red": [
        [0 / 500, 0x00 / 256, 0x00 / 256],
        [20 / 500, 0x00 / 256, 0x00 / 256],
        [40 / 500, 0xF9 / 256, 0xF9 / 256],
        [60 / 500, 0xE6 / 256, 0xE6 / 256],
        [100 / 500, 0xDD / 256, 0xDD / 256],
        [500 / 500, 0x96 / 256, 0x96 / 256],
    ],
    "green": [
        [0 / 500, 0x79 / 256, 0x79 / 256],
        [20 / 500, 0x79 / 256, 0x79 / 256],
        [40 / 500, 0xA8 / 256, 0xA8 / 256],
        [60 / 500, 0x51 / 256, 0x51 / 256],
        [100 / 500, 0x2C / 256, 0x2C / 256],
        [500 / 500, 0x00 / 256, 0x00 / 256],
    ],
    "blue": [
        [0 / 500, 0x6B / 256, 0x6B / 256],
        [20 / 500, 0x6B / 256, 0x6B / 256],
        [40 / 500, 0x25 / 256, 0x25 / 256],
        [60 / 500, 0x00 / 256, 0x00 / 256],
        [100 / 500, 0x00 / 256, 0x00 / 256],
        [500 / 500, 0x84 / 256, 0x84 / 256],
    ],
    "alpha": [[0.0, alpha, alpha], [1.0, alpha, alpha]],
}
color_map = LinearSegmentedColormap("LuftdatenPM2.5", segmentdata=cdict, N=500)
assert color_map(0.0) == (0x00 / 256, 0x79 / 256, 0x6B / 256, alpha), color_map(0.0)
assert color_map(1.0) == (0x96 / 256, 0x00 / 256, 0x84 / 256, alpha), color_map(1.0)


def conv_to_color(conc, alpha=125):
    r, g, b, _ = color_map(min(500, conc) / 500)
    return int(r * 256), int(g * 256), int(b * 256), alpha


hex_h2 = 20.0  # triangle side; half height
hex_h4 = hex_h2 / 2.0
hex_w2 = hex_h2 * sqrt(3) / 2.0
hex_grad = hex_h4 / hex_w2


class Hexagon(object):
    """Knows its (x, y) position, and holds data values too."""

    def __init__(self, x, y, data=None):
        """Initialise object with center point."""
        self.x = x
        self.y = y
        if data:
            self.data = data
        else:
            self.data = []

    def color(self):
        """Returns (R, G, B, Alpha) for the mean data value."""
        if not self.data:
            return None
        else:
            return conv_to_color(mean(self.data))

    def __contains__(self, other):
        """Is a point (x, y) within the hexagon?"""
        x0, y0 = self.x, self.y
        x1, y1 = other
        if x1 < x0 - hex_w2 or x0 + hex_w2 < x1:
            return False
        if y1 < y0 - hex_h2 or y0 + hex_h2 < y1:
            return False
        if y1 > y0 + hex_h4:
            # Could be in top triangle...
            if x0 < x1:
                # Top right, but above or below the slope?
                return (y1 - y0 - hex_h2) / (x1 - x0) < -hex_grad
            else:
                # Top left
                return hex_grad < (y1 - y0 - hex_h2) / (x1 - x0)
        elif y1 < y0 - hex_h4:
            # Could be in bottom triangle...
            if x0 < x1:
                # Bottom right
                return hex_grad < (y1 - y0 + hex_h2) / (x1 - x0)
            else:
                # Bottom left
                return (y1 - y0 + hex_h2) / (x1 - x0) < -hex_grad
        else:
            assert y0 - hex_h4 <= y1 <= y0 + hex_h4
            # Central rectangle
            return True

    def polygon(self):
        """Returns list of (x, y) values to draw the hexagon (floats)."""
        x, y = self.x, self.y
        return [
            (x, y + hex_h2),
            (x + hex_w2, y + hex_h4),
            (x + hex_w2, y - hex_h4),
            (x, y - hex_h2),
            (x - hex_w2, y - hex_h4),
            (x - hex_w2, y + hex_h4),
        ]


def draw_map(world_data, name, size, zoom, latitude, longitude, legend=0):
    print("https://maps.luftdaten.info/#%i/%0.2f/%0.2f" % (zoom, latitude, longitude))

    hexagons = []
    height, width = size
    tile_pair_h = 3 * hex_h2
    tile_w = 2 * hex_w2
    for row_pair in range(1 + int(height // tile_pair_h)):
        for col in range(1 + int(width // tile_w)):
            hexagons.append(Hexagon(col * tile_w, row_pair * tile_pair_h))
            hexagons.append(
                Hexagon(col * tile_w + hex_w2, row_pair * tile_pair_h + hex_h2 + hex_h4)
            )

    # Will use geotiler for map in background
    background_filename = "%s-background.png" % name
    geotiler_map = geotiler.Map(center=(longitude, latitude), zoom=zoom, size=size)
    min_long, min_lat, max_long, max_lat = map_extent = geotiler_map.extent
    if not os.path.isfile(background_filename):
        print("Fetching %s background" % name)
        map_img = geotiler.render_map(geotiler_map)
        map_img.save(background_filename)
    else:
        print("Loading %s background" % name)
        map_img = Image.open(background_filename)
    assert size == map_img.size

    # TODO - Apply filters to make the background muted
    # See https://www.w3schools.com/CSSref/css3_pr_filter.asp
    # and https://github.com/opendata-stuttgart/feinstaub-map/blob/master/src/style.style
    # img.leaflet-tile
    # filter  grayscale(85%) saturate(150%) hue-rotate(60deg) contrast(90%) brightness(110%)

    if legend:
        map_img.paste(legend_img, legend)
    else:
        map_img.paste(legend_img)

    data = [
        row
        for row in world_data
        if row["location"]["longitude"]
        and row["location"]["latitude"]
        and min_long <= float(row["location"]["longitude"]) <= max_long
        and min_lat <= float(row["location"]["latitude"]) <= max_lat
    ]
    print("Have %i points with map extent" % len(data))

    data_pm10 = []
    data_long = []
    data_lat = []
    for row in data:
        for sensor_data_value in row["sensordatavalues"]:
            if sensor_data_value["value_type"] == "P1":
                data_pm10.append(float(sensor_data_value["value"]))
                data_long.append(float(row["location"]["longitude"]))
                data_lat.append(float(row["location"]["latitude"]))

    data_x, data_y = zip(
        *(geotiler_map.rev_geocode(p) for p in zip(data_long, data_lat))
    )

    print("%i PM 10, %i long, %i lat" % (len(data_pm10), len(data_long), len(data_lat)))
    assert len(data_pm10) == len(data_long) == len(data_lat)

    # Make a blank image for the hexagon overlay,
    # initialized to a completely transparent color.
    hex_img = Image.new("RGBA", size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(hex_img, "RGBA")
    for x, y, value in zip(data_x, data_y, data_pm10):
        for hex in hexagons:
            if (x, y) in hex:
                hex.data.append(value)
                break

    print(
        "Worst hexagon mean PM 10 value %0.2f ug/m3"
        % max(mean(_.data) for _ in hexagons if _.data)
    )
    print("Worst PM 10 sensor value %0.2f ug/m3" % max(data_pm10))

    for hex in hexagons:
        if hex.data:
            draw.polygon(hex.polygon(), hex.color())
        # else:
        #     draw.polygon(hex.polygon(), (0,0,0xff,0xC0))

    # Debug code to check hexagons contain the points
    # for x, y, value in zip(data_x, data_y, data_pm10):
    #     if value:
    #         draw.polygon(
    #             [(x - 5, y - 5), (x - 5, y + 5), (x + 5, y + 5), (x + 5, y - 5)],
    #             (255, 0, 255, 125),
    #         )

    # Alpha composite the two images together.
    img = Image.alpha_composite(map_img, hex_img)
    img.save("%s.png" % name)
    print("%s done" % name)


for job in jobs:
    draw_map(
        world_data,
        job["name"],
        job.get("size", (600, 600)),
        job.get("zoom", 12),
        job["latitude"],
        job["longitude"],
        job.get("legend", (0, 0)),
    )
