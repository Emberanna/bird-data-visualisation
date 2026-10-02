import os
import calendar

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap, Normalize


# ============================================================
# 1. BASIC SETTINGS
# ============================================================

plt.close("all")

DATA_FILE = "data/migration-data.csv"
OUTPUT_FILE = "out/migration_coordinates.png"

SPECIES = "Brown Pelican"

BACKGROUND = "#080C11"

TEXT_MAIN = "#F0F3F5"
TEXT_SECONDARY = "#9BA7AF"
TEXT_DIM = "#65717A"

GUIDE = "#36434D"
DIVIDER = "#28333B"


# ============================================================
# 2. LOAD DATA
# ============================================================

data = pd.read_csv(DATA_FILE)

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

data = data[
    data["species"] == SPECIES
].copy()

data = data[
    data["longitude"].between(-180, 180)
    & data["latitude"].between(-90, 90)
].copy()

data = data.sort_values(
    ["bird_id", "timestamp"]
)


# ============================================================
# 3. SELECT ONE BIRD
# ============================================================

data["date"] = (
    data["timestamp"]
    .dt.floor("D")
)

bird_day_counts = (
    data.groupby("bird_id")["date"]
    .nunique()
    .sort_values(ascending=False)
)

selected_bird_id = bird_day_counts.index[0]

bird = data[
    data["bird_id"] == selected_bird_id
].copy()

bird = (
    bird.sort_values("timestamp")
    .reset_index(drop=True)
)


# ============================================================
# 4. NEXT GPS POSITION
# ============================================================

bird["next_lon"] = (
    bird["longitude"]
    .shift(-1)
)

bird["next_lat"] = (
    bird["latitude"]
    .shift(-1)
)

bird["next_time"] = (
    bird["timestamp"]
    .shift(-1)
)

bird["time_gap_hours"] = (
    (
        bird["next_time"]
        - bird["timestamp"]
    )
    .dt.total_seconds()
    / 3600
)


# ============================================================
# 5. HAVERSINE DISTANCE
# ============================================================

def haversine(
    lon1,
    lat1,
    lon2,
    lat2
):

    lon1 = np.radians(lon1)
    lat1 = np.radians(lat1)

    lon2 = np.radians(lon2)
    lat2 = np.radians(lat2)

    dlon = lon2 - lon1
    dlat = lat2 - lat1

    a = (
        np.sin(dlat / 2) ** 2
        +
        np.cos(lat1)
        *
        np.cos(lat2)
        *
        np.sin(dlon / 2) ** 2
    )

    a = np.clip(
        a,
        0,
        1
    )

    return (
        6371
        *
        2
        *
        np.arcsin(
            np.sqrt(a)
        )
    )


bird["distance_km"] = haversine(
    bird["longitude"],
    bird["latitude"],
    bird["next_lon"],
    bird["next_lat"]
)

# Ignore movement across long time gaps
bird.loc[
    bird["time_gap_hours"] > 48,
    "distance_km"
] = np.nan

# Ignore unrealistic GPS jumps
bird.loc[
    bird["distance_km"] > 500,
    "distance_km"
] = np.nan


# ============================================================
# 6. DAILY DATA
# ============================================================

daily = (
    bird.groupby(
        "date",
        as_index=False
    )
    .agg(
        distance_km=(
            "distance_km",
            "sum"
        ),

        gps_records=(
            "timestamp",
            "size"
        ),

        longitude=(
            "longitude",
            "mean"
        ),

        latitude=(
            "latitude",
            "mean"
        )
    )
)

daily["year"] = (
    daily["date"]
    .dt.year
)

daily["month"] = (
    daily["date"]
    .dt.month
)

daily["day"] = (
    daily["date"]
    .dt.day
)


# ============================================================
# 7. COLLAPSE YEARS INTO ONE ANNUAL CALENDAR
# ============================================================

annual_daily = (
    daily.groupby(
        ["month", "day"],
        as_index=False
    )
    .agg(
        distance_km=(
            "distance_km",
            "median"
        ),

        gps_records=(
            "gps_records",
            "median"
        ),

        longitude=(
            "longitude",
            "median"
        ),

        latitude=(
            "latitude",
            "median"
        ),

        years_observed=(
            "year",
            "nunique"
        )
    )
)


# ============================================================
# 8. MONTH SETTINGS
# ============================================================

month_names = [
    "JAN",
    "FEB",
    "MAR",
    "APR",
    "MAY",
    "JUN",
    "JUL",
    "AUG",
    "SEP",
    "OCT",
    "NOV",
    "DEC"
]

month_angles = np.linspace(
    0,
    2 * np.pi,
    12,
    endpoint=False
)


# ============================================================
# 9. GPS FILL COLOUR
#
# BLUE -> CYAN
# Circle fill = GPS records per day
# ============================================================

gps_cmap = (
    LinearSegmentedColormap
    .from_list(
        "gps_colour",
        [
            "#123B5A",
            "#126B88",
            "#1599AA",
            "#28BEC4",
            "#8DE6DF"
        ]
    )
)

gps_min = (
    annual_daily[
        "gps_records"
    ].min()
)

gps_max = (
    annual_daily[
        "gps_records"
    ].quantile(0.95)
)

if gps_max <= gps_min:
    gps_max = gps_min + 1

gps_norm = Normalize(
    vmin=gps_min,
    vmax=gps_max,
    clip=True
)


# ============================================================
# 10. GEOGRAPHIC POSITION
#
# BLUE -> DEEP PURPLE
#
# Circle EDGE = geographic position
# Longitude = horizontal colour change
# Latitude = vertical colour change
# ============================================================

lon_min = (
    annual_daily[
        "longitude"
    ].min()
)

lon_max = (
    annual_daily[
        "longitude"
    ].max()
)

lat_min = (
    annual_daily[
        "latitude"
    ].min()
)

lat_max = (
    annual_daily[
        "latitude"
    ].max()
)


def normalise(
    value,
    minimum,
    maximum
):

    if maximum == minimum:
        return 0.5

    return (
        (value - minimum)
        /
        (maximum - minimum)
    )


def geographic_colour(
    longitude,
    latitude
):

    x = normalise(
        longitude,
        lon_min,
        lon_max
    )

    y = normalise(
        latitude,
        lat_min,
        lat_max
    )

    x = np.clip(
        x,
        0,
        1
    )

    y = np.clip(
        y,
        0,
        1
    )

    # Southwest:
    # cyan / teal
    southwest = np.array(
        [
            0.08,
            0.67,
            0.68
        ]
    )

    # Southeast:
    # medium blue
    southeast = np.array(
        [
            0.16,
            0.47,
            0.78
        ]
    )

    # Northwest:
    # darker blue
    northwest = np.array(
        [
            0.18,
            0.52,
            0.72
        ]
    )

    # Northeast:
    # noticeably deeper purple
    northeast = np.array(
        [
            0.24,
            0.12,
            0.52
        ]
    )

    south = (
        southwest
        * (1 - x)
        +
        southeast
        * x
    )

    north = (
        northwest
        * (1 - x)
        +
        northeast
        * x
    )

    colour = (
        south
        * (1 - y)
        +
        north
        * y
    )

    return tuple(
        np.clip(
            colour,
            0,
            1
        )
    )


# ============================================================
# 11. DISTANCE SCALE
# ============================================================

positive_distance = (
    annual_daily[
        annual_daily[
            "distance_km"
        ] > 0
    ][
        "distance_km"
    ]
)

if len(positive_distance) > 0:

    distance_max = (
        positive_distance
        .quantile(0.95)
    )

else:

    distance_max = 1

if distance_max <= 0:
    distance_max = 1


# ============================================================
# 12. CREATE HORIZONTAL CANVAS
# ============================================================

fig = plt.figure(
    figsize=(
        16,
        10
    ),
    facecolor=BACKGROUND
)


# ============================================================
# 13. TITLE AREA
# ============================================================

fig.text(
    0.045,
    0.950,
    "Annual Migration Rhythm",
    color=TEXT_MAIN,
    fontsize=27,
    fontweight="normal",
    ha="left",
    va="top"
)

fig.text(
    0.045,
    0.902,
    (
        "Daily movement and geographic rhythm "
        "of one tracked Brown Pelican"
    ),
    color=TEXT_MAIN,
    fontsize=13,
    ha="left",
    va="top"
)

fig.text(
    0.045,
    0.868,
    (
        "12 connected months form one annual cycle"
        "  •  each branch represents one month"
        "  •  weekly nodes mark 7-day intervals"
    ),
    color=TEXT_SECONDARY,
    fontsize=8,
    ha="left",
    va="top"
)


# ============================================================
# 14. MAIN RADIAL CHART
# ============================================================

ax = fig.add_axes(
    [
        0.025,
        0.060,
        0.680,
        0.785
    ],
    projection="polar"
)

ax.set_facecolor(
    BACKGROUND
)

ax.set_theta_zero_location(
    "N"
)

ax.set_theta_direction(
    -1
)

ax.set_ylim(
    0,
    1.16
)

ax.set_xticks([])
ax.set_yticks([])

ax.grid(False)

ax.spines[
    "polar"
].set_visible(False)


# ============================================================
# 15. CENTRAL YEAR RING
# ============================================================

RING_RADIUS = 0.27
BRANCH_START = 0.36
BRANCH_END = 1.02

ring_theta = np.linspace(
    0,
    2 * np.pi,
    500
)

ax.plot(
    ring_theta,
    np.full(
        len(ring_theta),
        RING_RADIUS
    ),
    color="#53616B",
    linewidth=1.2,
    alpha=0.80,
    zorder=2
)


# ============================================================
# 16. MONTH CONNECTION POINTS
# ============================================================

ax.scatter(
    month_angles,
    np.full(
        12,
        RING_RADIUS
    ),
    s=38,
    facecolor="#D0E5E5",
    edgecolor=BACKGROUND,
    linewidth=1.0,
    zorder=20
)


# ============================================================
# 17. MONTH LABELS
# ============================================================

MONTH_LABEL_RADIUS = 0.315

for index, angle in enumerate(
    month_angles
):

    ax.text(
        angle,
        MONTH_LABEL_RADIUS,
        month_names[index],
        color="#D9E1E4",
        fontsize=7.5,
        fontweight="bold",
        ha="center",
        va="center",
        zorder=30
    )


# ============================================================
# 18. MONTH BRANCHES
# ============================================================

for angle in month_angles:

    ax.plot(
        [
            angle,
            angle
        ],
        [
            BRANCH_START,
            BRANCH_END
        ],
        color="#334550",
        linewidth=0.7,
        alpha=0.55,
        zorder=1
    )


# ============================================================
# 19. DAILY CIRCLES
# ============================================================

for month_number in range(
    1,
    13
):

    month_data = annual_daily[
        annual_daily[
            "month"
        ]
        == month_number
    ].copy()

    if len(month_data) == 0:
        continue

    angle = month_angles[
        month_number - 1
    ]

    max_day = calendar.monthrange(
        2024,
        month_number
    )[1]

    for _, row in month_data.iterrows():

        day = int(
            row["day"]
        )

        day_fraction = (
            (day - 1)
            /
            max(
                max_day - 1,
                1
            )
        )

        radius = (
            BRANCH_START
            +
            day_fraction
            *
            (
                BRANCH_END
                -
                BRANCH_START
            )
        )

        distance = row[
            "distance_km"
        ]

        if pd.isna(distance):
            distance = 0

        distance_normalised = min(
            distance
            /
            distance_max,
            1
        )

        circle_size = (
            14
            +
            (
                distance_normalised
                ** 1.18
            )
            *
            540
        )

        # Circle interior
        # = GPS records/day
        fill_colour = gps_cmap(
            gps_norm(
                row[
                    "gps_records"
                ]
            )
        )

        # Circle edge
        # = longitude + latitude
        edge_colour = geographic_colour(
            row[
                "longitude"
            ],
            row[
                "latitude"
            ]
        )

        # --------------------------------------------
        # SOFT GLOW
        # --------------------------------------------

        ax.scatter(
            [angle],
            [radius],
            s=circle_size * 2.0,
            color=fill_colour,
            alpha=0.040,
            edgecolors="none",
            zorder=3
        )

        ax.scatter(
            [angle],
            [radius],
            s=circle_size * 1.40,
            color=fill_colour,
            alpha=0.075,
            edgecolors="none",
            zorder=4
        )

        # --------------------------------------------
        # MAIN DAILY CIRCLE
        #
        # IMPORTANT:
        # thinner geographic-position outline
        # --------------------------------------------

        ax.scatter(
            [angle],
            [radius],
            s=circle_size,
            facecolor=fill_colour,
            edgecolor=edge_colour,
            linewidth=1.1,
            alpha=0.88,
            zorder=6
        )


# ============================================================
# 20. WEEKLY NODES
# ============================================================

week_days = [
    7,
    14,
    21,
    28
]

for month_number in range(
    1,
    13
):

    angle = month_angles[
        month_number - 1
    ]

    max_day = calendar.monthrange(
        2024,
        month_number
    )[1]

    for week_number, day in enumerate(
        week_days,
        start=1
    ):

        day_fraction = (
            (day - 1)
            /
            max(
                max_day - 1,
                1
            )
        )

        radius = (
            BRANCH_START
            +
            day_fraction
            *
            (
                BRANCH_END
                -
                BRANCH_START
            )
        )

        ax.scatter(
            [angle],
            [radius],
            s=15,
            facecolor=BACKGROUND,
            edgecolor="#E3E7E8",
            linewidth=0.8,
            zorder=15
        )

        # W1-W4 only shown on January

        if month_number == 1:

            ax.annotate(
                f"W{week_number}",
                xy=(
                    angle,
                    radius
                ),
                xytext=(
                    9,
                    0
                ),
                textcoords="offset points",
                color=TEXT_SECONDARY,
                fontsize=6,
                ha="left",
                va="center",
                zorder=20
            )


# ============================================================
# 21. CENTRE LABEL
# ============================================================

ax.scatter(
    [0],
    [0],
    s=650,
    facecolor=BACKGROUND,
    edgecolor="#52616A",
    linewidth=0.8,
    zorder=25
)

ax.text(
    0,
    0,
    "ONE\nYEAR",
    color=TEXT_SECONDARY,
    fontsize=6.5,
    ha="center",
    va="center",
    linespacing=1.2,
    zorder=30
)


# ============================================================
# 22. RIGHT INFORMATION PANEL
#
# KEEP THE NEW LAYOUT
# ============================================================

PANEL_X = 0.745
PANEL_RIGHT = 0.965

PANEL_WIDTH = (
    PANEL_RIGHT
    -
    PANEL_X
)


# ============================================================
# 23. HOW TO READ
# ============================================================

fig.text(
    PANEL_X,
    0.845,
    "HOW TO READ",
    color=TEXT_MAIN,
    fontsize=10,
    fontweight="bold",
    ha="left",
    va="top"
)

fig.text(
    PANEL_X,
    0.815,
    (
        "Each branch represents one month.\n"
        "Each circle represents one calendar day.\n"
        "Weekly nodes mark 7-day intervals."
    ),
    color=TEXT_SECONDARY,
    fontsize=7.4,
    ha="left",
    va="top",
    linespacing=1.55
)

# Divider 1

fig.lines.append(
    plt.Line2D(
        [
            PANEL_X,
            PANEL_RIGHT
        ],
        [
            0.742,
            0.742
        ],
        transform=fig.transFigure,
        color=DIVIDER,
        linewidth=0.8
    )
)


# ============================================================
# 24. TRACKED INDIVIDUAL
# ============================================================

fig.text(
    PANEL_X,
    0.715,
    "TRACKED INDIVIDUAL",
    color=TEXT_MAIN,
    fontsize=10,
    fontweight="bold",
    ha="left",
    va="top"
)

fig.text(
    PANEL_X,
    0.685,
    (
        f"Bird ID        {selected_bird_id}\n"
        f"GPS records    {len(bird):,}\n"
        f"Tracked days   {daily['date'].nunique():,}\n"
        f"Tracked years  {daily['year'].nunique()}"
    ),
    color=TEXT_SECONDARY,
    fontsize=7.4,
    ha="left",
    va="top",
    linespacing=1.55
)

# Divider 2

fig.lines.append(
    plt.Line2D(
        [
            PANEL_X,
            PANEL_RIGHT
        ],
        [
            0.585,
            0.585
        ],
        transform=fig.transFigure,
        color=DIVIDER,
        linewidth=0.8
    )
)


# ============================================================
# 25. CIRCLE SIZE — DAILY MOVEMENT
# ============================================================

fig.text(
    PANEL_X,
    0.555,
    "CIRCLE SIZE — DAILY MOVEMENT",
    color=TEXT_MAIN,
    fontsize=10,
    fontweight="bold",
    ha="left",
    va="top"
)

fig.text(
    PANEL_X,
    0.525,
    "Larger circles represent longer daily movement.",
    color=TEXT_SECONDARY,
    fontsize=7.2,
    ha="left",
    va="top"
)

size_ax = fig.add_axes(
    [
        PANEL_X,
        0.455,
        PANEL_WIDTH,
        0.055
    ]
)

size_ax.set_facecolor(
    BACKGROUND
)

size_ax.set_xlim(
    0,
    1
)

size_ax.set_ylim(
    0,
    1
)

size_ax.axis(
    "off"
)

distance_examples = [
    distance_max * 0.20,
    distance_max * 0.50,
    distance_max * 0.85
]

example_x = [
    0.16,
    0.49,
    0.82
]

for x, value in zip(
    example_x,
    distance_examples
):

    normalised_value = (
        value
        /
        distance_max
    )

    example_size = (
        14
        +
        (
            normalised_value
            ** 1.18
        )
        *
        540
    )

    size_ax.scatter(
        [x],
        [0.62],
        s=example_size,
        facecolor="#278FA4",
        edgecolor="#59D0D0",
        linewidth=1.0,
        alpha=0.85
    )

    size_ax.text(
        x,
        0.05,
        f"{value:.0f} km",
        color=TEXT_SECONDARY,
        fontsize=6.5,
        ha="center",
        va="bottom"
    )


# Divider 3

fig.lines.append(
    plt.Line2D(
        [
            PANEL_X,
            PANEL_RIGHT
        ],
        [
            0.425,
            0.425
        ],
        transform=fig.transFigure,
        color=DIVIDER,
        linewidth=0.8
    )
)


# ============================================================
# 26. CIRCLE FILL — GPS RECORDS
# ============================================================

fig.text(
    PANEL_X,
    0.395,
    "CIRCLE FILL — GPS RECORDS",
    color=TEXT_MAIN,
    fontsize=10,
    fontweight="bold",
    ha="left",
    va="top"
)

fig.text(
    PANEL_X,
    0.365,
    "Brighter fill = more GPS observations that day.",
    color=TEXT_SECONDARY,
    fontsize=7.2,
    ha="left",
    va="top"
)

gps_ax = fig.add_axes(
    [
        PANEL_X,
        0.325,
        PANEL_WIDTH,
        0.014
    ]
)

gps_gradient = np.linspace(
    0,
    1,
    256
).reshape(
    1,
    -1
)

gps_ax.imshow(
    gps_gradient,
    aspect="auto",
    cmap=gps_cmap
)

gps_ax.set_xticks(
    [
        0,
        255
    ]
)

gps_ax.set_xticklabels(
    [
        "FEWER",
        "MORE"
    ],
    color=TEXT_DIM,
    fontsize=6
)

gps_ax.set_yticks([])

gps_ax.tick_params(
    axis="x",
    length=0,
    pad=5
)

for spine in gps_ax.spines.values():

    spine.set_visible(
        False
    )


# Divider 4

fig.lines.append(
    plt.Line2D(
        [
            PANEL_X,
            PANEL_RIGHT
        ],
        [
            0.285,
            0.285
        ],
        transform=fig.transFigure,
        color=DIVIDER,
        linewidth=0.8
    )
)


# ============================================================
# 27. CIRCLE EDGE — GEOGRAPHIC POSITION
# ============================================================

fig.text(
    PANEL_X,
    0.255,
    "CIRCLE EDGE — GEOGRAPHIC POSITION",
    color=TEXT_MAIN,
    fontsize=9.4,
    fontweight="bold",
    ha="left",
    va="top"
)

fig.text(
    PANEL_X,
    0.225,
    (
        "Longitude controls horizontal colour change.\n"
        "Latitude controls vertical colour change."
    ),
    color=TEXT_SECONDARY,
    fontsize=7.0,
    ha="left",
    va="top",
    linespacing=1.40
)


# ============================================================
# 28. 2D GEOGRAPHIC COLOUR LEGEND
#
# BLUE -> DEEP PURPLE
# ============================================================

geo_ax = fig.add_axes(
    [
        PANEL_X + 0.020,
        0.075,
        PANEL_WIDTH - 0.040,
        0.105
    ]
)

grid_size = 100

geo_image = np.zeros(
    (
        grid_size,
        grid_size,
        3
    )
)

for row in range(
    grid_size
):

    for column in range(
        grid_size
    ):

        longitude = (
            lon_min
            +
            (
                column
                /
                (
                    grid_size
                    - 1
                )
            )
            *
            (
                lon_max
                -
                lon_min
            )
        )

        latitude = (
            lat_min
            +
            (
                row
                /
                (
                    grid_size
                    - 1
                )
            )
            *
            (
                lat_max
                -
                lat_min
            )
        )

        geo_image[
            row,
            column
        ] = geographic_colour(
            longitude,
            latitude
        )

geo_ax.imshow(
    geo_image,
    origin="lower",
    aspect="auto"
)

geo_ax.set_xticks([])
geo_ax.set_yticks([])

for spine in geo_ax.spines.values():

    spine.set_color(
        "#53616B"
    )

    spine.set_linewidth(
        0.7
    )


# WEST

geo_ax.text(
    0,
    -0.16,
    "WEST",
    transform=geo_ax.transAxes,
    color=TEXT_DIM,
    fontsize=6,
    ha="left",
    va="top"
)


# EAST

geo_ax.text(
    1,
    -0.16,
    "EAST",
    transform=geo_ax.transAxes,
    color=TEXT_DIM,
    fontsize=6,
    ha="right",
    va="top"
)


# SOUTH

geo_ax.text(
    -0.045,
    0,
    "S",
    transform=geo_ax.transAxes,
    color=TEXT_DIM,
    fontsize=6,
    ha="right",
    va="center"
)


# NORTH

geo_ax.text(
    -0.045,
    1,
    "N",
    transform=geo_ax.transAxes,
    color=TEXT_DIM,
    fontsize=6,
    ha="right",
    va="center"
)


# ============================================================
# 29. SAVE
# ============================================================

os.makedirs(
    "out",
    exist_ok=True
)

plt.savefig(
    OUTPUT_FILE,
    dpi=300,
    facecolor=BACKGROUND
)

print(
    "=========================================="
)

print(
    f"Saved: {OUTPUT_FILE}"
)

print(
    f"Bird ID: {selected_bird_id}"
)

print(
    f"GPS records: {len(bird):,}"
)

print(
    f"Tracked days: {daily['date'].nunique():,}"
)

print(
    f"Tracked years: {daily['year'].nunique()}"
)

print(
    "=========================================="
)

plt.show()

plt.close(fig)