# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#     "pandas",
#     "numpy",
#     "matplotlib",
#     "cartopy",
# ]
# ///

"""
BROWN PELICAN — MIGRATION THROUGH TIME

RAW GPS PARTICLES
-----------------
7,030 original GPS records are drawn as small glowing particles.

DAILY CIRCLES
-------------
816 tracked days are drawn as larger circles.

Position = real longitude / latitude
Colour   = year
Size     = daily movement distance
Density  = repeated GPS observations

2013 = blue
2014 = green
2015 = pink
"""

import os
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker

import cartopy.crs as ccrs
import cartopy.feature as cfeature


# ============================================================
# 01. SETTINGS
# ============================================================

DATA_FILE = "data/migration-data.csv"
OUTPUT_FILE = "out/migration_glow_map.png"

SPECIES = "Brown Pelican"
BIRD_ID = "AU48"


# ============================================================
# 02. COLOURS
# ============================================================

BACKGROUND = "#020405"
LAND_COLOR = "#070B0D"
OCEAN_COLOR = "#020405"

COAST_COLOR = "#667078"
BORDER_COLOR = "#515A60"
STATE_COLOR = "#3B444A"
GRID_COLOR = "#33434C"

TEXT_COLOR = "#F4F4F4"
MUTED_TEXT = "#9AA2A8"


YEAR_COLORS = {
    2013: "#13BFFF",   # BLUE
    2014: "#39F044",   # GREEN
    2015: "#FF168D",   # PINK
}


# ============================================================
# 03. DAILY CIRCLE DIAMETER
#
# Minimum visual diameter = 2
# Maximum visual diameter = 6
#
# scatter() uses area, so diameter is squared later.
# ============================================================

MIN_DIAMETER = 2.0
MAX_DIAMETER = 6.0

# Overall display scale
CIRCLE_SCALE = 5.0


# ============================================================
# 04. HAVERSINE
# ============================================================

def haversine(lon1, lat1, lon2, lat2):

    R = 6371.0

    lon1 = np.radians(lon1)
    lat1 = np.radians(lat1)
    lon2 = np.radians(lon2)
    lat2 = np.radians(lat2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        np.sin(dlat / 2.0) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2.0) ** 2
    )

    c = 2 * np.arctan2(
        np.sqrt(a),
        np.sqrt(1 - a)
    )

    return R * c


# ============================================================
# 05. LOAD DATA
# ============================================================

print()
print("Loading migration data...")

df = pd.read_csv(DATA_FILE)

df["timestamp"] = pd.to_datetime(
    df["timestamp"],
    errors="coerce"
)

df = df.dropna(
    subset=[
        "timestamp",
        "longitude",
        "latitude",
        "bird_id",
        "species",
    ]
)

df = df[
    df["longitude"].between(-180, 180)
    & df["latitude"].between(-90, 90)
].copy()


# ============================================================
# 06. SELECT AU48
# ============================================================

bird = df[
    (df["species"] == SPECIES)
    & (df["bird_id"].astype(str) == BIRD_ID)
].copy()

if bird.empty:

    raise ValueError(
        f"No data found for {SPECIES}, Bird ID {BIRD_ID}"
    )

bird = bird.sort_values(
    "timestamp"
).reset_index(drop=True)


# ============================================================
# 07. DATE INFORMATION
# ============================================================

bird["date"] = bird["timestamp"].dt.floor("D")
bird["year"] = bird["timestamp"].dt.year
bird["month"] = bird["timestamp"].dt.month


# ============================================================
# 08. CALCULATE SEGMENT DISTANCE
# ============================================================

bird["prev_lon"] = bird["longitude"].shift(1)
bird["prev_lat"] = bird["latitude"].shift(1)
bird["prev_time"] = bird["timestamp"].shift(1)


bird["time_gap_hours"] = (
    bird["timestamp"]
    - bird["prev_time"]
).dt.total_seconds() / 3600.0


bird["segment_km"] = haversine(
    bird["prev_lon"],
    bird["prev_lat"],
    bird["longitude"],
    bird["latitude"]
)


# Ignore large temporal gaps
bird.loc[
    bird["time_gap_hours"] > 48,
    "segment_km"
] = np.nan


# Ignore unrealistic jumps
bird.loc[
    bird["segment_km"] > 500,
    "segment_km"
] = np.nan


# ============================================================
# 09. DAILY DATA
#
# ONE ROW = ONE TRACKED DAY
# ============================================================

daily = (
    bird
    .groupby("date")
    .agg(
        longitude=("longitude", "median"),
        latitude=("latitude", "median"),
        distance_km=("segment_km", "sum"),
        gps_records=("timestamp", "count"),
    )
    .reset_index()
)


daily["year"] = daily["date"].dt.year
daily["month"] = daily["date"].dt.month


daily = daily.sort_values(
    "date"
).reset_index(drop=True)


# ============================================================
# 10. YEARS
# ============================================================

years = sorted(
    int(year)
    for year in daily["year"].unique()
)


# ============================================================
# 11. DATA SUMMARY
# ============================================================

print()
print("=" * 60)
print("DATA SUMMARY")
print("=" * 60)

print(
    "Bird ID:",
    BIRD_ID
)

print(
    "Raw GPS records:",
    f"{len(bird):,}"
)

print(
    "Tracked days:",
    f"{len(daily):,}"
)

print(
    "Years:",
    years
)

print()

for year in years:

    raw_count = len(
        bird[
            bird["year"] == year
        ]
    )

    day_count = len(
        daily[
            daily["year"] == year
        ]
    )

    print(
        year,
        "→",
        f"{raw_count:,}",
        "GPS records /",
        day_count,
        "days"
    )

print("=" * 60)


# ============================================================
# 12. DAILY MOVEMENT SIZE
#
# IMPORTANT CHANGE:
#
# Instead of ordinary linear scaling based on raw distance,
# we use percentile rank.
#
# This preserves the order:
# longer movement = larger circle
#
# but spreads the 816 days across the FULL 2 → 6 range.
#
# Therefore size differences become much easier to see.
# ============================================================

daily["distance_rank"] = (
    daily["distance_km"]
    .rank(
        method="average",
        pct=True
    )
    .fillna(0)
)


daily["visual_diameter"] = (
    MIN_DIAMETER
    + daily["distance_rank"]
    * (
        MAX_DIAMETER
        - MIN_DIAMETER
    )
)


# scatter uses area
daily["point_size"] = (
    daily["visual_diameter"] ** 2
) * CIRCLE_SCALE


# ============================================================
# 13. GPS RECORD BRIGHTNESS
# ============================================================

gps_min = daily[
    "gps_records"
].min()

gps_max = daily[
    "gps_records"
].quantile(0.95)


if gps_max <= gps_min:
    gps_max = gps_min + 1


daily["gps_norm"] = (
    (
        daily["gps_records"]
        - gps_min
    )
    /
    (
        gps_max
        - gps_min
    )
)


daily["gps_norm"] = np.clip(
    daily["gps_norm"],
    0,
    1
)


# ============================================================
# 14. MAP EXTENT
# ============================================================

lon_min = daily["longitude"].min()
lon_max = daily["longitude"].max()

lat_min = daily["latitude"].min()
lat_max = daily["latitude"].max()


lon_range = lon_max - lon_min
lat_range = lat_max - lat_min


lon_pad = max(
    lon_range * 0.055,
    0.25
)

lat_pad = max(
    lat_range * 0.20,
    0.30
)


extent = [
    lon_min - lon_pad,
    lon_max + lon_pad,
    lat_min - lat_pad,
    lat_max + lat_pad,
]


# ============================================================
# 15. FIGURE
# ============================================================

fig = plt.figure(
    figsize=(18, 9),
    facecolor=BACKGROUND
)


# ============================================================
# 16. MAP AREA
# ============================================================

ax = fig.add_axes(
    [
        0.055,
        0.10,
        0.695,
        0.80,
    ],
    projection=ccrs.PlateCarree()
)


ax.set_facecolor(
    BACKGROUND
)


ax.set_extent(
    extent,
    crs=ccrs.PlateCarree()
)


# ============================================================
# 17. LAND + OCEAN
# ============================================================

ax.add_feature(
    cfeature.OCEAN.with_scale("10m"),
    facecolor=OCEAN_COLOR,
    edgecolor="none",
    zorder=0
)


ax.add_feature(
    cfeature.LAND.with_scale("10m"),
    facecolor=LAND_COLOR,
    edgecolor="none",
    zorder=0
)


# ============================================================
# 18. MAP DETAILS
# ============================================================

ax.add_feature(
    cfeature.COASTLINE.with_scale("10m"),
    edgecolor=COAST_COLOR,
    linewidth=0.65,
    alpha=0.78,
    zorder=1
)


ax.add_feature(
    cfeature.BORDERS.with_scale("10m"),
    edgecolor=BORDER_COLOR,
    linewidth=0.42,
    alpha=0.65,
    zorder=1
)


try:

    ax.add_feature(
        cfeature.STATES.with_scale("10m"),
        edgecolor=STATE_COLOR,
        facecolor="none",
        linewidth=0.36,
        alpha=0.65,
        zorder=1
    )

except Exception:

    pass


# ============================================================
# 19. GRIDLINES
# ============================================================

gridlines = ax.gridlines(
    crs=ccrs.PlateCarree(),
    draw_labels=True,
    linewidth=0.38,
    color=GRID_COLOR,
    alpha=0.60,
    linestyle=":",
    x_inline=False,
    y_inline=False
)


gridlines.top_labels = False
gridlines.right_labels = False


gridlines.xlabel_style = {
    "size": 8.5,
    "color": MUTED_TEXT,
}

gridlines.ylabel_style = {
    "size": 8.5,
    "color": MUTED_TEXT,
}

gridlines.rotate_labels = False


# ============================================================
# 20. GRID SPACING
# ============================================================

def choose_grid_step(data_range):

    if data_range <= 3:
        return 0.5

    if data_range <= 6:
        return 1

    if data_range <= 12:
        return 2

    if data_range <= 20:
        return 4

    return 5


lon_step = choose_grid_step(
    extent[1] - extent[0]
)

lat_step = choose_grid_step(
    extent[3] - extent[2]
)


lon_start = (
    np.floor(extent[0] / lon_step)
    * lon_step
)

lon_end = (
    np.ceil(extent[1] / lon_step)
    * lon_step
)

lat_start = (
    np.floor(extent[2] / lat_step)
    * lat_step
)

lat_end = (
    np.ceil(extent[3] / lat_step)
    * lat_step
)


gridlines.xlocator = mticker.FixedLocator(
    np.arange(
        lon_start,
        lon_end + lon_step,
        lon_step
    )
)


gridlines.ylocator = mticker.FixedLocator(
    np.arange(
        lat_start,
        lat_end + lat_step,
        lat_step
    )
)


# ============================================================
# 21. NORTH AMERICA
# ============================================================

continent_lon = (
    extent[0]
    + (
        extent[1]
        - extent[0]
    ) * 0.055
)


continent_lat = (
    extent[3]
    - (
        extent[3]
        - extent[2]
    ) * 0.08
)


ax.text(
    continent_lon,
    continent_lat,
    "N O R T H   A M E R I C A",
    transform=ccrs.PlateCarree(),
    color="#AEB4B8",
    fontsize=16,
    alpha=0.45,
    ha="left",
    va="top",
    zorder=2
)


# ============================================================
# 22. AXIS TITLES
# ============================================================

fig.text(
    0.402,
    0.055,
    "LONGITUDE",
    color=MUTED_TEXT,
    fontsize=8.5,
    ha="center"
)


fig.text(
    0.018,
    0.50,
    "LATITUDE",
    color=MUTED_TEXT,
    fontsize=8.5,
    rotation=90,
    ha="center",
    va="center"
)


# ============================================================
# 23. RAW GPS PARTICLES
#
# MAJOR CHANGE:
#
# Draw ALL 7,030 original GPS records.
#
# These are NOT random points.
# These are NOT generated coordinates.
#
# Every particle is a real GPS observation.
#
# Multiple observations naturally overlap and form
# luminous geographic fields.
# ============================================================

for year in years:

    raw_year = bird[
        bird["year"] == year
    ].copy()

    colour = YEAR_COLORS.get(
        year,
        "#FFFFFF"
    )


    # --------------------------------------------------------
    # VERY SOFT GPS HALO
    # --------------------------------------------------------

    ax.scatter(
        raw_year["longitude"],
        raw_year["latitude"],
        s=30,
        color=colour,
        alpha=0.010,
        edgecolors="none",
        transform=ccrs.PlateCarree(),
        zorder=2
    )


    # --------------------------------------------------------
    # MEDIUM GPS GLOW
    # --------------------------------------------------------

    ax.scatter(
        raw_year["longitude"],
        raw_year["latitude"],
        s=12,
        color=colour,
        alpha=0.025,
        edgecolors="none",
        transform=ccrs.PlateCarree(),
        zorder=3
    )


    # --------------------------------------------------------
    # REAL GPS PARTICLES
    # --------------------------------------------------------

    ax.scatter(
        raw_year["longitude"],
        raw_year["latitude"],
        s=3.2,
        color=colour,
        alpha=0.25,
        edgecolors="none",
        transform=ccrs.PlateCarree(),
        zorder=4
    )


    # --------------------------------------------------------
    # TINY BRIGHT GPS CORE
    # --------------------------------------------------------

    ax.scatter(
        raw_year["longitude"],
        raw_year["latitude"],
        s=0.65,
        color="#FFFFFF",
        alpha=0.10,
        edgecolors="none",
        transform=ccrs.PlateCarree(),
        zorder=5
    )


# ============================================================
# 24. TRAJECTORY LINES
# ============================================================

for year in years:

    year_data = daily[
        daily["year"] == year
    ].copy()

    year_data = year_data.sort_values(
        "date"
    ).reset_index(drop=True)


    colour = YEAR_COLORS.get(
        year,
        "#FFFFFF"
    )


    year_data["gap_days"] = (
        year_data["date"]
        .diff()
        .dt.days
    )


    year_data["trajectory_group"] = (
        year_data["gap_days"]
        .fillna(0)
        .gt(7)
        .cumsum()
    )


    for _, segment in year_data.groupby(
        "trajectory_group"
    ):

        if len(segment) < 2:
            continue


        # faint outer trajectory
        ax.plot(
            segment["longitude"],
            segment["latitude"],
            transform=ccrs.PlateCarree(),
            color=colour,
            linewidth=1.2,
            alpha=0.025,
            zorder=6
        )


        # thin actual trajectory
        ax.plot(
            segment["longitude"],
            segment["latitude"],
            transform=ccrs.PlateCarree(),
            color=colour,
            linewidth=0.38,
            alpha=0.22,
            zorder=7
        )


# ============================================================
# 25. DAILY CIRCLES
#
# ALL 816 tracked days.
#
# Glow is intentionally restrained here so that
# circle SIZE remains visible.
# ============================================================

for year in years:

    year_data = daily[
        daily["year"] == year
    ].copy()


    colour = YEAR_COLORS.get(
        year,
        "#FFFFFF"
    )


    for _, row in year_data.iterrows():

        lon = row["longitude"]
        lat = row["latitude"]

        size = row["point_size"]
        gps = row["gps_norm"]


        # ----------------------------------------------------
        # SMALL OUTER GLOW
        # ----------------------------------------------------

        ax.scatter(
            lon,
            lat,
            s=size * 2.3,
            color=colour,
            alpha=0.025 + gps * 0.025,
            edgecolors="none",
            transform=ccrs.PlateCarree(),
            zorder=8
        )


        # ----------------------------------------------------
        # INNER GLOW
        # ----------------------------------------------------

        ax.scatter(
            lon,
            lat,
            s=size * 1.45,
            color=colour,
            alpha=0.07 + gps * 0.06,
            edgecolors="none",
            transform=ccrs.PlateCarree(),
            zorder=9
        )


        # ----------------------------------------------------
        # MAIN DAILY CIRCLE
        # ----------------------------------------------------

        ax.scatter(
            lon,
            lat,
            s=size,
            facecolor=colour,
            edgecolor=colour,
            linewidth=0.35,
            alpha=0.55 + gps * 0.40,
            transform=ccrs.PlateCarree(),
            zorder=10
        )


        # ----------------------------------------------------
        # BRIGHT CENTRE
        # ----------------------------------------------------

        if gps > 0.40:

            strength = (
                gps - 0.40
            ) / 0.60


            centre_size = (
                size
                * 0.10
                * strength
            )


            ax.scatter(
                lon,
                lat,
                s=max(
                    centre_size,
                    1
                ),
                color="#FFFFFF",
                alpha=0.25 + strength * 0.70,
                edgecolors="none",
                transform=ccrs.PlateCarree(),
                zorder=11
            )


# ============================================================
# 26. MAP BORDER
# ============================================================

try:

    ax.spines[
        "geo"
    ].set_edgecolor(
        "#59636A"
    )

    ax.spines[
        "geo"
    ].set_linewidth(
        0.55
    )

except Exception:

    pass


# ============================================================
# 27. RIGHT PANEL
# ============================================================

info = fig.add_axes(
    [
        0.785,
        0.075,
        0.19,
        0.85,
    ]
)


info.set_facecolor(
    BACKGROUND
)

info.set_xlim(
    0,
    1
)

info.set_ylim(
    0,
    1
)

info.axis(
    "off"
)


# ============================================================
# 28. TITLE
# ============================================================

info.text(
    0.0,
    0.975,
    "BROWN PELICAN",
    color=TEXT_COLOR,
    fontsize=20,
    fontweight="bold",
    va="top"
)


info.text(
    0.0,
    0.928,
    "MIGRATION THROUGH TIME",
    color=MUTED_TEXT,
    fontsize=9.5
)


info.text(
    0.0,
    0.895,
    "Daily movement across tracked years",
    color=MUTED_TEXT,
    fontsize=7.2
)


info.plot(
    [0.0, 0.96],
    [0.858, 0.858],
    color="#3B4145",
    linewidth=0.7
)


# ============================================================
# 29. HOW TO READ
# ============================================================

info.text(
    0.0,
    0.820,
    "HOW TO READ",
    color=MUTED_TEXT,
    fontsize=7.5
)


info.text(
    0.0,
    0.785,
    "ONE CIRCLE = ONE TRACKED DAY",
    color=TEXT_COLOR,
    fontsize=9,
    fontweight="bold"
)


info.text(
    0.0,
    0.752,
    "Small particles = raw GPS records",
    color=MUTED_TEXT,
    fontsize=7
)


info.text(
    0.0,
    0.725,
    "Position = real longitude / latitude",
    color=MUTED_TEXT,
    fontsize=7
)


# ============================================================
# 30. INDIVIDUAL
# ============================================================

info.text(
    0.0,
    0.675,
    "TRACKED INDIVIDUAL",
    color=MUTED_TEXT,
    fontsize=7.5
)


info.text(
    0.0,
    0.638,
    f"BIRD  {BIRD_ID}",
    color=TEXT_COLOR,
    fontsize=13,
    fontweight="bold"
)


info.text(
    0.0,
    0.603,
    f"{len(daily):,} TRACKED DAYS",
    color=MUTED_TEXT,
    fontsize=8
)


info.text(
    0.0,
    0.575,
    f"{len(bird):,} GPS RECORDS",
    color=MUTED_TEXT,
    fontsize=8
)


# ============================================================
# 31. YEAR LEGEND
# ============================================================

info.text(
    0.0,
    0.525,
    "TRACKED YEAR",
    color=MUTED_TEXT,
    fontsize=7.5
)


year_y = [
    0.478,
    0.408,
    0.338
]


for year, y in zip(
    years,
    year_y
):

    colour = YEAR_COLORS.get(
        year,
        "#FFFFFF"
    )


    day_count = len(
        daily[
            daily["year"] == year
        ]
    )


    # glow
    info.scatter(
        0.055,
        y,
        s=220,
        color=colour,
        alpha=0.05,
        edgecolors="none"
    )

    info.scatter(
        0.055,
        y,
        s=90,
        color=colour,
        alpha=0.18,
        edgecolors="none"
    )

    info.scatter(
        0.055,
        y,
        s=32,
        color=colour,
        alpha=1,
        edgecolors="none"
    )

    info.scatter(
        0.055,
        y,
        s=5,
        color="#FFFFFF",
        alpha=0.95,
        edgecolors="none"
    )


    info.text(
        0.16,
        y + 0.008,
        str(year),
        color=TEXT_COLOR,
        fontsize=11,
        fontweight="bold",
        va="center"
    )


    info.text(
        0.16,
        y - 0.023,
        f"{day_count} tracked days",
        color=MUTED_TEXT,
        fontsize=6.8,
        va="center"
    )


# ============================================================
# 32. DAILY MOVEMENT LEGEND
# ============================================================

info.text(
    0.0,
    0.260,
    "DAILY MOVEMENT",
    color=MUTED_TEXT,
    fontsize=7.5
)


info.text(
    0.0,
    0.225,
    "CIRCLE SIZE",
    color=TEXT_COLOR,
    fontsize=10,
    fontweight="bold"
)


# Diameter:
# 2, 3, 4.5, 6

legend_diameters = [
    2.0,
    3.0,
    4.5,
    6.0
]


size_x = [
    0.08,
    0.27,
    0.48,
    0.72
]


for x, diameter in zip(
    size_x,
    legend_diameters
):

    size = (
        diameter ** 2
    ) * CIRCLE_SCALE


    info.scatter(
        x,
        0.172,
        s=size,
        facecolors="none",
        edgecolors="#E5E7E8",
        linewidths=0.9
    )


# ------------------------------------------------------------
# SIZE ARROW
# ------------------------------------------------------------

info.annotate(
    "",
    xy=(0.66, 0.125),
    xytext=(0.18, 0.125),
    arrowprops=dict(
        arrowstyle="-|>",
        color=MUTED_TEXT,
        linewidth=0.7
    )
)


info.text(
    0.0,
    0.121,
    "SHORT",
    color=MUTED_TEXT,
    fontsize=6
)


info.text(
    0.70,
    0.121,
    "LONG",
    color=MUTED_TEXT,
    fontsize=6
)


# ============================================================
# 33. GPS DENSITY LEGEND
# ============================================================

info.text(
    0.0,
    0.075,
    "GPS RECORDS",
    color=MUTED_TEXT,
    fontsize=7.5
)


info.text(
    0.0,
    0.042,
    "POINT DENSITY",
    color=TEXT_COLOR,
    fontsize=10,
    fontweight="bold"
)


density_x = [
    0.08,
    0.28,
    0.49,
    0.72
]


density_alpha = [
    0.20,
    0.40,
    0.70,
    1.00
]


legend_colour = YEAR_COLORS[
    2015
]


for x, strength in zip(
    density_x,
    density_alpha
):

    info.scatter(
        x,
        0.003,
        s=130,
        color=legend_colour,
        alpha=0.03 * strength,
        edgecolors="none"
    )

    info.scatter(
        x,
        0.003,
        s=50,
        color=legend_colour,
        alpha=0.12 * strength,
        edgecolors="none"
    )

    info.scatter(
        x,
        0.003,
        s=12,
        color=legend_colour,
        alpha=strength,
        edgecolors="none"
    )


# ============================================================
# 34. SAVE
# ============================================================

os.makedirs(
    "out",
    exist_ok=True
)


plt.savefig(
    OUTPUT_FILE,
    dpi=300,
    facecolor=BACKGROUND,
    bbox_inches="tight",
    pad_inches=0.10
)


# ============================================================
# 35. CLOSE
# ============================================================

plt.close(fig)


# ============================================================
# 36. FINAL CHECK
# ============================================================

print()
print("=" * 60)
print("VISUALISATION FINISHED")
print("=" * 60)

print()
print("Saved to:")
print(OUTPUT_FILE)

print()
print(
    "RAW GPS PARTICLES:",
    f"{len(bird):,}"
)

print(
    "DAILY CIRCLES:",
    f"{len(daily):,}"
)

print()

for year in years:

    raw_count = len(
        bird[
            bird["year"] == year
        ]
    )

    day_count = len(
        daily[
            daily["year"] == year
        ]
    )

    print(
        year,
        "→",
        f"{raw_count:,}",
        "GPS particles +",
        day_count,
        "daily circles"
    )

print()
print(
    "Circle diameter:",
    "2 → 6"
)

print("=" * 60)