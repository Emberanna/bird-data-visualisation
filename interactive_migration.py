# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#     "pandas",
#     "numpy",
#     "matplotlib",
#     "cartopy",
# ]
# ///

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

from matplotlib.widgets import Button
from matplotlib.animation import FuncAnimation

import cartopy.crs as ccrs
import cartopy.feature as cfeature


# ============================================================
# 01. SETTINGS
# ============================================================

DATA_FILE = "data/migration-data.csv"

SPECIES = "Brown Pelican"
BIRD_ID = "AU48"

BACKGROUND = "#020405"
LAND_COLOR = "#070B0D"

TEXT_COLOR = "#F4F4F4"
MUTED_TEXT = "#929CA2"

BUTTON_COLOR = "#111619"
BUTTON_HOVER = "#30383D"

YEAR_COLORS = {
    2013: "#13BFFF",
    2014: "#39F044",
    2015: "#FF168D",
}

MONTH_NAMES = {
    1: "JAN",
    2: "FEB",
    3: "MAR",
    4: "APR",
    5: "MAY",
    6: "JUN",
    7: "JUL",
    8: "AUG",
    9: "SEP",
    10: "OCT",
    11: "NOV",
    12: "DEC",
}


# ============================================================
# 02. HAVERSINE
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
# 03. LOAD DATA
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
# 04. SELECT BIRD
# ============================================================

bird = df[
    (df["species"] == SPECIES)
    & (df["bird_id"].astype(str) == BIRD_ID)
].copy()

if bird.empty:
    raise ValueError(
        "No Brown Pelican AU48 data found."
    )

bird = (
    bird
    .sort_values("timestamp")
    .reset_index(drop=True)
)

bird["date"] = bird["timestamp"].dt.floor("D")
bird["year"] = bird["timestamp"].dt.year
bird["month"] = bird["timestamp"].dt.month


# ============================================================
# 05. MOVEMENT DISTANCE
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

bird.loc[
    bird["time_gap_hours"] > 48,
    "segment_km"
] = np.nan

bird.loc[
    bird["segment_km"] > 500,
    "segment_km"
] = np.nan


# ============================================================
# 06. DAILY SUMMARY
# ============================================================

daily = (
    bird
    .groupby("date")
    .agg(
        longitude=("longitude", "median"),
        latitude=("latitude", "median"),
        distance_km=("segment_km", "sum"),
        gps_records=("timestamp", "count"),
        first_record=("timestamp", "min"),
        last_record=("timestamp", "max"),
    )
    .reset_index()
)

daily["year"] = daily["date"].dt.year
daily["month"] = daily["date"].dt.month

daily = (
    daily
    .sort_values("date")
    .reset_index(drop=True)
)


# ============================================================
# 07. POINT SIZE
# ============================================================

daily["distance_rank"] = (
    daily["distance_km"]
    .rank(
        method="average",
        pct=True
    )
    .fillna(0)
)

daily["point_size"] = (
    18
    + daily["distance_rank"] * 145
)


# ============================================================
# 08. STATE
# ============================================================

years = sorted(
    int(x)
    for x in daily["year"].unique()
)

selected_mode = "ALL"
selected_year = None
selected_month = None

displayed_daily = pd.DataFrame()

animation = None
animation_running = False
playback_index = 0


# ============================================================
# 09. FIGURE
# ============================================================

fig = plt.figure(
    figsize=(17, 9),
    facecolor=BACKGROUND
)


# ============================================================
# MAP POSITION
#
# IMPORTANT:
# The whole map is moved upward.
#
# NORTH AMERICA stays where it is.
# ============================================================

ax = fig.add_axes(
    [
        0.055,   # left
        0.285,   # bottom -> moved UP
        0.685,   # width
        0.625    # height
    ],
    projection=ccrs.PlateCarree()
)

ax.set_facecolor(
    BACKGROUND
)


# ============================================================
# 10. MAP EXTENT
# ============================================================

lon_min = daily["longitude"].min()
lon_max = daily["longitude"].max()

lat_min = daily["latitude"].min()
lat_max = daily["latitude"].max()

lon_range = lon_max - lon_min
lat_range = lat_max - lat_min

extent = [
    lon_min - max(lon_range * 0.06, 0.35),
    lon_max + max(lon_range * 0.06, 0.35),

    # Keep extra vertical space
    lat_min - max(lat_range * 0.55, 0.70),
    lat_max + max(lat_range * 0.55, 0.70),
]

ax.set_extent(
    extent,
    crs=ccrs.PlateCarree()
)


# ============================================================
# 11. BASE MAP
# ============================================================

ax.add_feature(
    cfeature.OCEAN.with_scale("10m"),
    facecolor=BACKGROUND,
    edgecolor="none"
)

ax.add_feature(
    cfeature.LAND.with_scale("10m"),
    facecolor=LAND_COLOR,
    edgecolor="none"
)

ax.add_feature(
    cfeature.COASTLINE.with_scale("10m"),
    edgecolor="#59636A",
    linewidth=0.55,
    alpha=0.72
)

ax.add_feature(
    cfeature.BORDERS.with_scale("10m"),
    edgecolor="#414A50",
    linewidth=0.35,
    alpha=0.42
)

try:

    ax.add_feature(
        cfeature.STATES.with_scale("10m"),
        edgecolor="#353D42",
        facecolor="none",
        linewidth=0.30,
        alpha=0.42
    )

except Exception:
    pass


# ============================================================
# 12. LONGITUDE / LATITUDE
# ============================================================

gridlines = ax.gridlines(
    crs=ccrs.PlateCarree(),
    draw_labels=True,

    # Very subtle grid
    linewidth=0.22,
    color="#829097",
    alpha=0.07,
    linestyle="-",

    x_inline=False,
    y_inline=False
)

gridlines.top_labels = False
gridlines.right_labels = False

gridlines.xlabel_style = {
    "size": 8,
    "color": "#A0ADB4",
}

gridlines.ylabel_style = {
    "size": 8,
    "color": "#A0ADB4",
}


# ============================================================
# 13. NORTH AMERICA
#
# DO NOT MOVE
# Same height as INTERACTIVE MIGRATION
# ============================================================

fig.text(
    0.3975,
    0.892,
    "NORTH AMERICA",
    color="#A1AAAF",
    fontsize=10,
    fontweight="bold",
    alpha=0.85,
    ha="center",
    va="center"
)


# ============================================================
# 14. GEOGRAPHIC LABELS
# ============================================================

LAND_LABEL_COLOR = "#69747A"


# GULF OF MEXICO
# Approximately 29°N / 87°W

ax.text(
    -87.0,
    29.0,
    "GULF OF MEXICO",
    transform=ccrs.PlateCarree(),
    color="#71838D",
    fontsize=8,
    fontstyle="italic",
    alpha=0.46,
    ha="center",
    va="center",
    zorder=2
)


# LOUISIANA

ax.text(
    -89.55,
    30.82,
    "LOUISIANA",
    transform=ccrs.PlateCarree(),
    color=LAND_LABEL_COLOR,
    fontsize=6.0,
    alpha=0.50,
    ha="center",
    va="center",
    zorder=2
)


# MISSISSIPPI

ax.text(
    -88.95,
    30.98,
    "MISSISSIPPI",
    transform=ccrs.PlateCarree(),
    color=LAND_LABEL_COLOR,
    fontsize=5.6,
    alpha=0.50,
    ha="center",
    va="center",
    zorder=2
)


# ALABAMA

ax.text(
    -87.75,
    30.98,
    "ALABAMA",
    transform=ccrs.PlateCarree(),
    color=LAND_LABEL_COLOR,
    fontsize=5.8,
    alpha=0.50,
    ha="center",
    va="center",
    zorder=2
)


# FLORIDA

ax.text(
    -83.05,
    30.25,
    "FLORIDA",
    transform=ccrs.PlateCarree(),
    color=LAND_LABEL_COLOR,
    fontsize=6.2,
    alpha=0.52,
    ha="center",
    va="center",
    rotation=-8,
    zorder=2
)


# ============================================================
# 15. RIGHT PANEL — TITLE
# ============================================================

fig.text(
    0.78,
    0.925,
    "BROWN PELICAN",
    color=TEXT_COLOR,
    fontsize=18,
    fontweight="bold"
)

fig.text(
    0.78,
    0.892,
    "INTERACTIVE MIGRATION",
    color=MUTED_TEXT,
    fontsize=9
)

fig.text(
    0.78,
    0.852,
    f"BIRD {BIRD_ID}",
    color=TEXT_COLOR,
    fontsize=10,
    fontweight="bold"
)

fig.text(
    0.78,
    0.823,
    f"{len(bird):,} GPS RECORDS",
    color=MUTED_TEXT,
    fontsize=8
)

fig.text(
    0.78,
    0.798,
    f"{len(daily):,} TRACKED DAYS",
    color=MUTED_TEXT,
    fontsize=8
)


# ============================================================
# 16. STATUS
# ============================================================

status_text = fig.text(
    0.78,
    0.755,
    "",
    color=TEXT_COLOR,
    fontsize=11,
    fontweight="bold"
)

date_text = fig.text(
    0.78,
    0.720,
    "",
    color=MUTED_TEXT,
    fontsize=9
)


# ============================================================
# 17. DAILY DETAIL PANEL
#
# Directly below:
# SEP / OCT / NOV / DEC
# ============================================================

detail_title = fig.text(
    0.78,
    0.285,
    "CLICK A DAILY POINT",
    color=MUTED_TEXT,
    fontsize=7,
    fontweight="bold"
)

detail_date = fig.text(
    0.78,
    0.255,
    "",
    color=TEXT_COLOR,
    fontsize=8,
    fontweight="bold"
)

detail_distance = fig.text(
    0.78,
    0.228,
    "",
    color=MUTED_TEXT,
    fontsize=7
)

detail_records = fig.text(
    0.78,
    0.201,
    "",
    color=MUTED_TEXT,
    fontsize=7
)


# ============================================================
# 18. MONTH COMPARISON
#
# Appears underneath daily information
# ============================================================

comparison_title = fig.text(
    0.78,
    0.160,
    "",
    color=TEXT_COLOR,
    fontsize=8,
    fontweight="bold"
)

comparison_2013 = fig.text(
    0.78,
    0.128,
    "",
    color=YEAR_COLORS.get(2013, TEXT_COLOR),
    fontsize=7
)

comparison_2014 = fig.text(
    0.78,
    0.098,
    "",
    color=YEAR_COLORS.get(2014, TEXT_COLOR),
    fontsize=7
)

comparison_2015 = fig.text(
    0.78,
    0.068,
    "",
    color=YEAR_COLORS.get(2015, TEXT_COLOR),
    fontsize=7
)


# ============================================================
# 19. SINGLE-YEAR ARTISTS
# ============================================================

single_glow, = ax.plot(
    [],
    [],
    linewidth=6,
    alpha=0.08,
    transform=ccrs.PlateCarree(),
    zorder=4
)

single_line, = ax.plot(
    [],
    [],
    linewidth=1.35,
    alpha=0.85,
    transform=ccrs.PlateCarree(),
    zorder=5
)

single_gps = ax.scatter(
    [],
    [],
    s=4,
    alpha=0.28,
    edgecolors="none",
    transform=ccrs.PlateCarree(),
    zorder=3
)

single_daily = ax.scatter(
    [],
    [],
    s=[],
    alpha=0.85,
    picker=True,
    pickradius=8,
    transform=ccrs.PlateCarree(),
    zorder=8
)


# ============================================================
# 20. ALL-YEAR ARTISTS
# ============================================================

all_lines = {}
all_glows = {}
all_points = {}
all_visible_data = {}

for year in years:

    colour = YEAR_COLORS[year]

    glow, = ax.plot(
        [],
        [],
        color=colour,
        linewidth=6,
        alpha=0.07,
        transform=ccrs.PlateCarree(),
        zorder=4
    )

    line, = ax.plot(
        [],
        [],
        color=colour,
        linewidth=1.35,
        alpha=0.82,
        transform=ccrs.PlateCarree(),
        zorder=5
    )

    points = ax.scatter(
        [],
        [],
        s=[],
        color=colour,
        alpha=0.80,
        picker=True,
        pickradius=8,
        transform=ccrs.PlateCarree(),
        zorder=7
    )

    all_glows[year] = glow
    all_lines[year] = line
    all_points[year] = points


selected_marker = ax.scatter(
    [],
    [],
    s=250,
    facecolors="none",
    edgecolors="#FFFFFF",
    linewidths=1.5,
    transform=ccrs.PlateCarree(),
    zorder=10
)


# ============================================================
# 21. CLEAR / RESET
# ============================================================

def clear_comparison():

    comparison_title.set_text("")
    comparison_2013.set_text("")
    comparison_2014.set_text("")
    comparison_2015.set_text("")


def reset_details():

    detail_date.set_text("")
    detail_distance.set_text("")
    detail_records.set_text("")

    selected_marker.set_offsets(
        np.empty((0, 2))
    )


def hide_single():

    single_line.set_data([], [])
    single_glow.set_data([], [])

    single_gps.set_offsets(
        np.empty((0, 2))
    )

    single_daily.set_offsets(
        np.empty((0, 2))
    )

    single_daily.set_sizes(
        np.array([])
    )


def hide_all():

    for year in years:

        all_lines[year].set_data([], [])
        all_glows[year].set_data([], [])

        all_points[year].set_offsets(
            np.empty((0, 2))
        )

        all_points[year].set_sizes(
            np.array([])
        )


def stop_timer():

    global animation_running

    animation_running = False

    if (
        animation is not None
        and animation.event_source is not None
    ):
        animation.event_source.stop()


# ============================================================
# 22. DRAW SINGLE YEAR
# ============================================================

def draw_single(data):

    global displayed_daily

    hide_all()

    displayed_daily = (
        data
        .copy()
        .reset_index(drop=True)
    )

    if displayed_daily.empty:

        hide_single()
        fig.canvas.draw_idle()
        return


    colour = YEAR_COLORS[
        selected_year
    ]

    single_line.set_color(colour)
    single_glow.set_color(colour)
    single_gps.set_color(colour)

    single_daily.set_facecolor(colour)
    single_daily.set_edgecolor(colour)


    x = displayed_daily[
        "longitude"
    ].to_numpy()

    y = displayed_daily[
        "latitude"
    ].to_numpy()


    single_line.set_data(x, y)
    single_glow.set_data(x, y)

    single_daily.set_offsets(
        np.column_stack([x, y])
    )

    single_daily.set_sizes(
        displayed_daily[
            "point_size"
        ].to_numpy()
    )


    start_date = displayed_daily[
        "date"
    ].min()

    end_date = (
        displayed_daily[
            "date"
        ].max()
        + pd.Timedelta(days=1)
    )

    raw = bird[
        (bird["timestamp"] >= start_date)
        & (bird["timestamp"] < end_date)
    ]

    if raw.empty:

        single_gps.set_offsets(
            np.empty((0, 2))
        )

    else:

        single_gps.set_offsets(
            np.column_stack([
                raw["longitude"].to_numpy(),
                raw["latitude"].to_numpy()
            ])
        )


    fig.canvas.draw_idle()


# ============================================================
# 23. DRAW STATIC ALL YEARS
# ============================================================

def draw_all_years(month=None):

    global all_visible_data

    hide_single()

    all_visible_data = {}


    for year in years:

        data = daily[
            daily["year"] == year
        ].copy()


        if month is not None:

            data = data[
                data["month"] == month
            ].copy()


        data = (
            data
            .sort_values("date")
            .reset_index(drop=True)
        )

        all_visible_data[year] = data


        if data.empty:

            all_lines[year].set_data([], [])
            all_glows[year].set_data([], [])

            all_points[year].set_offsets(
                np.empty((0, 2))
            )

            all_points[year].set_sizes(
                np.array([])
            )

            continue


        x = data[
            "longitude"
        ].to_numpy()

        y = data[
            "latitude"
        ].to_numpy()


        all_lines[year].set_data(
            x,
            y
        )

        all_glows[year].set_data(
            x,
            y
        )

        all_points[year].set_offsets(
            np.column_stack([x, y])
        )

        all_points[year].set_sizes(
            data[
                "point_size"
            ].to_numpy()
        )


    fig.canvas.draw_idle()


# ============================================================
# 24. MONTH COMPARISON
# ============================================================

def update_month_comparison(month):

    comparison_title.set_text(
        f"{MONTH_NAMES[month]} — MONTH COMPARISON"
    )

    text_objects = {
        2013: comparison_2013,
        2014: comparison_2014,
        2015: comparison_2015,
    }


    for year in years:

        month_data = daily[
            (daily["year"] == year)
            & (daily["month"] == month)
        ]

        distance = (
            month_data["distance_km"]
            .sum()
        )

        records = int(
            month_data["gps_records"]
            .sum()
        )

        days = len(
            month_data
        )

        text_value = (
            f"{year}   "
            f"{distance:,.1f} KM   "
            f"{records:,} GPS   "
            f"{days} DAYS"
        )

        if year in text_objects:

            text_objects[year].set_text(
                text_value
            )


# ============================================================
# 25. ALL YEARS
# ============================================================

def choose_all_years(event=None):

    global selected_mode
    global selected_year
    global selected_month

    stop_timer()

    selected_mode = "ALL"
    selected_year = None
    selected_month = None

    reset_details()
    clear_comparison()

    draw_all_years()

    status_text.set_text(
        "2013 + 2014 + 2015"
    )

    date_text.set_text(
        "STATIC YEAR COMPARISON"
    )

    fig.canvas.draw_idle()


# ============================================================
# 26. SELECT YEAR
# ============================================================

def choose_year(year):

    global selected_mode
    global selected_year
    global selected_month
    global playback_index

    stop_timer()

    selected_mode = "YEAR"
    selected_year = year
    selected_month = None

    playback_index = 0

    reset_details()
    clear_comparison()

    data = (
        daily[
            daily["year"] == year
        ]
        .sort_values("date")
        .reset_index(drop=True)
    )

    draw_single(data)

    status_text.set_text(
        f"{year} / FULL YEAR"
    )

    date_text.set_text(
        "PLAY / PAUSE AVAILABLE"
    )

    fig.canvas.draw_idle()


# ============================================================
# 27. SELECT MONTH
# ============================================================

def choose_month(month):

    global selected_month
    global playback_index

    stop_timer()

    selected_month = month

    reset_details()


    # ========================================================
    # ALL YEARS
    # ========================================================

    if selected_mode == "ALL":

        draw_all_years(
            month=month
        )

        status_text.set_text(
            f"ALL YEARS / {MONTH_NAMES[month]}"
        )

        date_text.set_text(
            "2013 + 2014 + 2015"
        )

        update_month_comparison(
            month
        )

        fig.canvas.draw_idle()

        return


    # ========================================================
    # SINGLE YEAR
    # ========================================================

    clear_comparison()

    month_data = (
        daily[
            (daily["year"] == selected_year)
            & (daily["month"] == month)
        ]
        .sort_values("date")
        .reset_index(drop=True)
    )

    draw_single(
        month_data
    )

    status_text.set_text(
        f"{selected_year} / {MONTH_NAMES[month]}"
    )


    if month_data.empty:

        date_text.set_text(
            "NO TRACKED DAYS"
        )

        return


    first = (
        month_data["date"]
        .min()
        .strftime("%d %b")
        .upper()
    )

    last = (
        month_data["date"]
        .max()
        .strftime("%d %b")
        .upper()
    )

    date_text.set_text(
        f"{first} → {last}"
    )


    year_data = (
        daily[
            daily["year"] == selected_year
        ]
        .sort_values("date")
        .reset_index(drop=True)
    )

    first_month_date = (
        month_data["date"].min()
    )

    matches = year_data.index[
        year_data["date"]
        >= first_month_date
    ]

    if len(matches) > 0:

        playback_index = int(
            matches[0]
        )


    fig.canvas.draw_idle()


# ============================================================
# 28. DAILY INFORMATION
# ============================================================

def update_day_information(row):

    current_date = pd.Timestamp(
        row["date"]
    )

    date_label = (
        current_date
        .strftime("%d %b %Y")
        .upper()
    )

    selected_marker.set_offsets(
        [[
            row["longitude"],
            row["latitude"]
        ]]
    )

    detail_date.set_text(
        date_label
    )

    detail_distance.set_text(
        f"MOVEMENT   {row['distance_km']:.1f} KM"
    )

    detail_records.set_text(
        f"GPS RECORDS   {int(row['gps_records'])}"
    )


# ============================================================
# 29. ANIMATION
# ============================================================

def animation_update(_):

    global playback_index
    global animation_running

    if selected_mode != "YEAR":
        return


    year_data = (
        daily[
            daily["year"] == selected_year
        ]
        .sort_values("date")
        .reset_index(drop=True)
    )


    if playback_index >= len(
        year_data
    ):

        animation_running = False

        if (
            animation is not None
            and animation.event_source is not None
        ):
            animation.event_source.stop()

        status_text.set_text(
            f"{selected_year} / COMPLETE"
        )

        return


    row = year_data.iloc[
        playback_index
    ]

    current_data = (
        year_data
        .iloc[
            : playback_index + 1
        ]
        .copy()
    )

    draw_single(
        current_data
    )

    current_date = pd.Timestamp(
        row["date"]
    )

    status_text.set_text(
        f"{selected_year} / PLAYING"
    )

    date_text.set_text(
        current_date
        .strftime("%d %b %Y")
        .upper()
    )

    update_day_information(
        row
    )

    playback_index += 1

    fig.canvas.draw_idle()


# ============================================================
# 30. PLAY
# ============================================================

def play_animation(event=None):

    global animation
    global animation_running
    global playback_index
    global selected_month


    if selected_mode != "YEAR":

        status_text.set_text(
            "SELECT ONE YEAR TO PLAY"
        )

        date_text.set_text(
            "ALL YEARS MODE IS STATIC"
        )

        fig.canvas.draw_idle()

        return


    selected_month = None


    year_data = daily[
        daily["year"] == selected_year
    ]


    if playback_index >= len(
        year_data
    ):

        playback_index = 0


    animation_running = True


    if animation is None:

        animation = FuncAnimation(
            fig,
            animation_update,
            frames=None,
            interval=85,
            repeat=True,
            cache_frame_data=False
        )

    else:

        # Continue from the current playback_index
        animation.event_source.start()


    fig.canvas.draw_idle()


# ============================================================
# 31. PAUSE
# ============================================================

def pause_animation(event=None):

    global animation_running

    if selected_mode != "YEAR":
        return


    animation_running = False


    if (
        animation is not None
        and animation.event_source is not None
    ):

        animation.event_source.stop()


    status_text.set_text(
        f"{selected_year} / PAUSED"
    )

    date_text.set_text(
        "PRESS PLAY TO CONTINUE"
    )

    fig.canvas.draw_idle()


# ============================================================
# 32. CLICK DAILY POINT
# ============================================================

def on_pick(event):

    # ========================================================
    # SINGLE YEAR
    # ========================================================

    if event.artist == single_daily:

        if displayed_daily.empty:
            return

        if len(event.ind) == 0:
            return

        index = int(
            event.ind[0]
        )

        if index >= len(
            displayed_daily
        ):
            return

        row = displayed_daily.iloc[
            index
        ]

        update_day_information(
            row
        )

        fig.canvas.draw_idle()

        return


    # ========================================================
    # ALL YEARS
    # ========================================================

    for year in years:

        if event.artist != all_points[year]:
            continue

        if len(event.ind) == 0:
            return

        data = all_visible_data.get(
            year,
            pd.DataFrame()
        )

        if data.empty:
            return

        index = int(
            event.ind[0]
        )

        if index >= len(data):
            return

        row = data.iloc[
            index
        ]

        update_day_information(
            row
        )

        fig.canvas.draw_idle()

        return


fig.canvas.mpl_connect(
    "pick_event",
    on_pick
)


# ============================================================
# 33. DISPLAY
# ============================================================

fig.text(
    0.78,
    0.670,
    "DISPLAY",
    color=MUTED_TEXT,
    fontsize=7,
    fontweight="bold"
)


all_ax = fig.add_axes(
    [
        0.78,
        0.620,
        0.18,
        0.038
    ]
)

all_button = Button(
    all_ax,
    "ALL YEARS",
    color=BUTTON_COLOR,
    hovercolor=BUTTON_HOVER
)

all_button.label.set_color(
    TEXT_COLOR
)

all_button.label.set_fontsize(
    8
)

all_button.on_clicked(
    choose_all_years
)


# ============================================================
# 34. YEAR BUTTONS
# ============================================================

year_buttons = []

year_x = {
    2013: 0.78,
    2014: 0.845,
    2015: 0.91,
}

for year in years:

    if year not in year_x:
        continue

    button_ax = fig.add_axes(
        [
            year_x[year],
            0.570,
            0.055,
            0.036
        ]
    )

    button = Button(
        button_ax,
        str(year),
        color=BUTTON_COLOR,
        hovercolor=YEAR_COLORS[year]
    )

    button.label.set_color(
        TEXT_COLOR
    )

    button.label.set_fontsize(
        8
    )

    button.on_clicked(
        lambda event, y=year:
        choose_year(y)
    )

    year_buttons.append(
        button
    )


# ============================================================
# 35. PLAY / PAUSE
# ============================================================

play_ax = fig.add_axes(
    [
        0.78,
        0.515,
        0.085,
        0.040
    ]
)

pause_ax = fig.add_axes(
    [
        0.875,
        0.515,
        0.085,
        0.040
    ]
)

play_button = Button(
    play_ax,
    "▶ PLAY",
    color=BUTTON_COLOR,
    hovercolor=BUTTON_HOVER
)

pause_button = Button(
    pause_ax,
    "Ⅱ PAUSE",
    color=BUTTON_COLOR,
    hovercolor=BUTTON_HOVER
)

play_button.label.set_color(
    TEXT_COLOR
)

pause_button.label.set_color(
    TEXT_COLOR
)

play_button.on_clicked(
    play_animation
)

pause_button.on_clicked(
    pause_animation
)


# ============================================================
# 36. MONTH
# ============================================================

fig.text(
    0.78,
    0.475,
    "MONTH",
    color=MUTED_TEXT,
    fontsize=7,
    fontweight="bold"
)

month_buttons = []

for month in range(1, 13):

    row = (month - 1) // 4
    col = (month - 1) % 4

    x = (
        0.78
        + col * 0.050
    )

    y = (
        0.425
        - row * 0.048
    )

    button_ax = fig.add_axes(
        [
            x,
            y,
            0.043,
            0.032
        ]
    )

    button = Button(
        button_ax,
        MONTH_NAMES[month],
        color=BUTTON_COLOR,
        hovercolor=BUTTON_HOVER
    )

    button.label.set_color(
        TEXT_COLOR
    )

    button.label.set_fontsize(
        7
    )

    button.on_clicked(
        lambda event, m=month:
        choose_month(m)
    )

    month_buttons.append(
        button
    )


# ============================================================
# 37. INITIAL VIEW
# ============================================================

choose_all_years()


# ============================================================
# 38. TERMINAL INFORMATION
# ============================================================

print()
print("=" * 60)
print("INTERACTIVE MIGRATION EXPLORER")
print("=" * 60)

print("Bird:", BIRD_ID)
print("GPS records:", f"{len(bird):,}")
print("Tracked days:", f"{len(daily):,}")
print("Years:", years)

print()
print("ALL YEARS = static comparison")
print("ALL YEARS + MONTH = compare month across years")
print("YEAR = single-year mode")
print("PLAY = animate selected year")
print("PAUSE = continue from current position")
print("POINT = inspect one tracked day")

print()
print("=" * 60)


# ============================================================
# 39. SHOW
# ============================================================

plt.show()