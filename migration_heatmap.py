import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import cartopy.crs as ccrs
import cartopy.feature as cfeature

from matplotlib.collections import LineCollection
from matplotlib.lines import Line2D

import os


# ============================================================
# 1. LOAD DATA
# ============================================================

data = pd.read_csv("data/migration-data.csv")

data["timestamp"] = pd.to_datetime(
    data["timestamp"],
    errors="coerce"
)

data = data.dropna(
    subset=[
        "timestamp",
        "longitude",
        "latitude",
        "bird_id",
        "species"
    ]
)


# ============================================================
# 2. KEEP ONLY BROWN PELICAN
# ============================================================

data = data[
    data["species"] == "Brown Pelican"
].copy()


# Remove impossible GPS coordinates
data = data[
    data["longitude"].between(-180, 180)
    & data["latitude"].between(-90, 90)
].copy()


# Sort each bird chronologically
data = data.sort_values(
    ["bird_id", "timestamp"]
)


# ============================================================
# 3. KEEP MONTH INFORMATION
# ============================================================
#
# Month is kept for the future interactive version:
#
# ALL | JAN | FEB | MAR ... DEC
#
# Month does NOT control colour in this overview.
# ============================================================

data["month"] = data["timestamp"].dt.month
data["year"] = data["timestamp"].dt.year


# ============================================================
# 4. FIND NEXT GPS POINT
# ============================================================

data["next_lon"] = (
    data
    .groupby("bird_id")["longitude"]
    .shift(-1)
)

data["next_lat"] = (
    data
    .groupby("bird_id")["latitude"]
    .shift(-1)
)

data["next_time"] = (
    data
    .groupby("bird_id")["timestamp"]
    .shift(-1)
)


# ============================================================
# 5. CALCULATE TIME GAP
# ============================================================

data["time_gap_hours"] = (
    data["next_time"]
    - data["timestamp"]
).dt.total_seconds() / 3600


# ============================================================
# 6. HAVERSINE DISTANCE
# ============================================================
#
# Distance is only used to detect suspicious GPS jumps.
#
# It does NOT control:
# - colour
# - brightness
# - line width
#
# ============================================================

def haversine(lon1, lat1, lon2, lat2):

    lon1 = np.radians(lon1)
    lat1 = np.radians(lat1)

    lon2 = np.radians(lon2)
    lat2 = np.radians(lat2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    a = np.clip(a, 0, 1)

    return (
        6371
        * 2
        * np.arcsin(np.sqrt(a))
    )


data["segment_distance_km"] = haversine(
    data["longitude"],
    data["latitude"],
    data["next_lon"],
    data["next_lat"]
)


# ============================================================
# 7. CREATE VALID MOVEMENT SEGMENTS
# ============================================================
#
# Remove:
# 1. Missing next GPS point
# 2. Time gaps larger than 48 hours
# 3. Suspicious jumps larger than 500 km
#
# ============================================================

segments_data = data[
    data["next_lon"].notna()
    & data["next_lat"].notna()
    & data["next_time"].notna()
].copy()


segments_data = segments_data[
    segments_data["time_gap_hours"] <= 48
].copy()


segments_data = segments_data[
    segments_data["segment_distance_km"] <= 500
].copy()


# ============================================================
# 8. DATA INFORMATION
# ============================================================

number_of_birds = data["bird_id"].nunique()
number_of_records = len(data)
number_of_segments = len(segments_data)


print()
print("========================================")
print("BROWN PELICAN MIGRATION FLOW")
print("========================================")

print(
    "Tracked individuals:",
    number_of_birds
)

print(
    "GPS records:",
    f"{number_of_records:,}"
)

print(
    "Movement segments:",
    f"{number_of_segments:,}"
)

print(
    "Date range:",
    data["timestamp"].min(),
    "to",
    data["timestamp"].max()
)

print()

print("GPS records by month:")

print(
    data.groupby("month").size()
)

print("========================================")
print()


# ============================================================
# 9. VISUAL STYLE
# ============================================================

BACKGROUND = "#111519"

LAND = "#292D2F"

OCEAN = "#171C20"

COAST = "#596166"

BORDER = "#3C4347"

TEXT_MAIN = "#F1F3F4"

TEXT_SECONDARY = "#A4ADB3"

TEXT_MAP = "#6E797F"


# Brown Pelican visual identity
ROUTE_COLOR = "#35B6C9"


# ============================================================
# 10. CREATE FIGURE
# ============================================================
#
# The map now occupies more of the canvas.
#
# ============================================================

fig = plt.figure(
    figsize=(14, 9),
    facecolor=BACKGROUND
)


ax = fig.add_axes(
    [
        0.025,   # left
        0.045,   # bottom
        0.950,   # width
        0.820    # height
    ],
    projection=ccrs.PlateCarree()
)


ax.set_facecolor(OCEAN)


# ============================================================
# 11. MAP EXTENT
# ============================================================
#
# Focus on the Gulf of Mexico and the main
# Brown Pelican tracking region.
#
# ============================================================

ax.set_extent(
    [
        -100.5,   # west
        -79.0,    # east
        17.0,     # south
        32.0      # north
    ],
    crs=ccrs.PlateCarree()
)


# ============================================================
# 12. DARK BASE MAP
# ============================================================

ax.add_feature(
    cfeature.OCEAN,
    facecolor=OCEAN,
    zorder=0
)


ax.add_feature(
    cfeature.LAND,
    facecolor=LAND,
    zorder=0
)


ax.add_feature(
    cfeature.LAKES,
    facecolor=OCEAN,
    edgecolor=COAST,
    linewidth=0.25,
    zorder=1
)


ax.add_feature(
    cfeature.COASTLINE,
    edgecolor=COAST,
    linewidth=0.55,
    zorder=1
)


ax.add_feature(
    cfeature.BORDERS,
    edgecolor=BORDER,
    linewidth=0.28,
    zorder=1
)


# Remove rectangular map border
for spine in ax.spines.values():
    spine.set_visible(False)


# ============================================================
# 13. GEOGRAPHIC LABELS
# ============================================================
#
# Same visual style for geographic labels.
#
# NORTH AMERICA has been moved inland so that
# it does not cover the migration trajectories.
#
# ============================================================

ax.text(
    -97.4,
    26.0,

    "NORTH\nAMERICA",

    transform=ccrs.PlateCarree(),

    fontsize=11,

    weight="normal",

    color=TEXT_MAP,

    alpha=0.65,

    ha="center",

    va="center",

    zorder=2
)


ax.text(
    -89.3,
    23.2,

    "GULF OF\nMEXICO",

    transform=ccrs.PlateCarree(),

    fontsize=12,

    weight="normal",

    color=TEXT_MAP,

    alpha=0.65,

    ha="center",

    va="center",

    zorder=2
)


# ============================================================
# 14. BUILD GPS LINE SEGMENTS
# ============================================================
#
# Every pair of consecutive GPS observations from
# the same bird becomes one small trajectory segment.
#
# ============================================================

starts = (
    segments_data[
        ["longitude", "latitude"]
    ]
    .to_numpy()
)


ends = (
    segments_data[
        ["next_lon", "next_lat"]
    ]
    .to_numpy()
)


line_segments = np.stack(
    [
        starts,
        ends
    ],
    axis=1
)


# ============================================================
# 15. SOFT GLOW LAYER
# ============================================================
#
# Same trajectories drawn wider and very transparent.
#
# This creates the subtle luminous migration-flow effect.
#
# ============================================================

glow = LineCollection(
    line_segments,

    colors=ROUTE_COLOR,

    linewidths=0.90,

    alpha=0.018,

    transform=ccrs.PlateCarree(),

    zorder=3
)


ax.add_collection(glow)


# ============================================================
# 16. MAIN MIGRATION TRAJECTORIES
# ============================================================
#
# One route = subtle
#
# Many overlapping routes = brighter
#
# No distance-based line width.
# No month-based colour.
#
# ============================================================

routes = LineCollection(
    line_segments,

    colors=ROUTE_COLOR,

    linewidths=0.28,

    alpha=0.065,

    transform=ccrs.PlateCarree(),

    zorder=4
)


ax.add_collection(routes)


# ============================================================
# 17. TITLE
# ============================================================
#
# Slightly smaller than the previous version
# so that the map becomes the main visual element.
#
# ============================================================

fig.text(
    0.045,
    0.955,

    "Nature's Flight Paths",

    fontsize=26,

    weight="normal",

    color=TEXT_MAIN
)


fig.text(
    0.045,
    0.910,

    "Travel routes of Brown Pelicans",

    fontsize=15,

    weight="normal",

    color=TEXT_MAIN
)


fig.text(
    0.045,
    0.875,

    (
        "GPS tracking reveals repeated movement corridors "
        "across multiple individuals"
    ),

    fontsize=9,

    color=TEXT_SECONDARY
)


# ============================================================
# 18. SPECIES LEGEND
# ============================================================

legend_elements = [

    Line2D(
        [0],
        [0],

        color=ROUTE_COLOR,

        linewidth=3,

        label="Brown Pelican"
    )

]


legend = ax.legend(
    handles=legend_elements,

    loc="lower right",

    title="TRACKED SPECIES",

    title_fontsize=8,

    fontsize=9,

    frameon=False,

    labelcolor=TEXT_MAIN
)


legend.get_title().set_color(
    TEXT_SECONDARY
)


# ============================================================
# 19. DATA INFORMATION
# ============================================================

info_text = (
    f"{number_of_birds} tracked individuals\n"
    f"{number_of_records:,} GPS records\n"
    f"{number_of_segments:,} movement segments"
)


ax.text(
    0.020,
    0.025,

    info_text,

    transform=ax.transAxes,

    fontsize=8,

    color=TEXT_SECONDARY,

    linespacing=1.55,

    ha="left",

    va="bottom",

    zorder=10
)


# ============================================================
# 20. VISUAL EXPLANATION
# ============================================================

fig.text(
    0.045,
    0.020,

    (
        "Each fine line connects consecutive GPS observations "
        "from the same tracked bird. "
        "Repeated trajectories overlap and appear brighter."
    ),

    fontsize=8,

    color="#7D878D"
)


# ============================================================
# 21. SAVE
# ============================================================

os.makedirs(
    "out",
    exist_ok=True
)


plt.savefig(
    "out/migration_heatmap.png",

    dpi=300,

    bbox_inches="tight",

    facecolor=fig.get_facecolor()
)


plt.show()