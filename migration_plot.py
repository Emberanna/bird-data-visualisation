import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import os


# --------------------------------------------------
# 1. Load data
# --------------------------------------------------

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

# ONLY KEEP BROWN PELICAN
data = data[
    data["species"] == "Brown Pelican"
].copy()

data = data.sort_values(
    ["bird_id", "timestamp"]
)


# --------------------------------------------------
# 2. Calculate movement between GPS points
# --------------------------------------------------

def prepare_bird(bird):

    bird = bird.sort_values("timestamp").copy()

    # Previous GPS location
    lat1 = np.radians(
        bird["latitude"].shift()
    )

    lat2 = np.radians(
        bird["latitude"]
    )

    dlat = lat2 - lat1

    dlon = np.radians(
        bird["longitude"]
        - bird["longitude"].shift()
    )

    # Haversine distance
    a = (
        np.sin(dlat / 2) ** 2
        + np.cos(lat1)
        * np.cos(lat2)
        * np.sin(dlon / 2) ** 2
    )

    a = a.clip(0, 1)

    distance = (
        6371
        * 2
        * np.arcsin(np.sqrt(a))
    )

    bird["distance_km"] = distance

    # Remove unrealistic jumps
    bird.loc[
        bird["distance_km"] > 500,
        "distance_km"
    ] = np.nan

    # Day of year
    bird["day"] = (
        bird["timestamp"].dt.dayofyear
    )

    return bird


# --------------------------------------------------
# 3. Create daily migration profile
# --------------------------------------------------

all_birds = []

for bird_id, bird in data.groupby("bird_id"):

    bird = prepare_bird(bird)

    daily = (
        bird
        .groupby("day")["distance_km"]
        .sum()
        .reindex(range(1, 367))
    )

    all_birds.append(daily)


# Combine all tracked Brown Pelicans
species_profile = pd.concat(
    all_birds,
    axis=1
)

# Median daily movement across birds
profile = species_profile.median(
    axis=1,
    skipna=True
).fillna(0)


# --------------------------------------------------
# 4. Scale
# --------------------------------------------------

positive_values = profile[
    profile > 0
].values

if len(positive_values) > 0:

    scale_max = np.percentile(
        positive_values,
        95
    )

else:

    scale_max = 1

if scale_max == 0:
    scale_max = 1


# --------------------------------------------------
# 5. Prepare radial data
# --------------------------------------------------

profile = profile.clip(
    upper=scale_max
)

values = profile.values

# Day of year -> angle
theta = np.linspace(
    0,
    2 * np.pi,
    len(values),
    endpoint=False
)

# Normalize radius
radius = values / scale_max


# --------------------------------------------------
# 6. Draw ONE large radial migration fingerprint
# --------------------------------------------------

fig = plt.figure(
    figsize=(10, 10),
    facecolor="#fafafa"
)

ax = fig.add_subplot(
    111,
    projection="polar"
)

# January at top
ax.set_theta_zero_location("N")

# Time moves clockwise
ax.set_theta_direction(-1)


# Main migration shape
ax.plot(
    theta,
    radius,
    linewidth=2.2,
    color="#1565c0"
)

ax.fill(
    theta,
    radius,
    alpha=0.16,
    color="#1565c0"
)


# --------------------------------------------------
# 7. Month positions
# --------------------------------------------------

month_days = np.array([
    1,
    32,
    60,
    91,
    121,
    152,
    182,
    213,
    244,
    274,
    305,
    335
])

month_angles = (
    (month_days - 1)
    / 366
    * 2
    * np.pi
)

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

ax.set_xticks(
    month_angles
)

ax.set_xticklabels(
    month_names,
    fontsize=10,
    weight="bold"
)


# --------------------------------------------------
# 8. Clean radial chart
# --------------------------------------------------

ax.set_yticklabels([])

ax.set_ylim(
    0,
    1
)

ax.grid(
    True,
    alpha=0.18
)

ax.spines["polar"].set_alpha(
    0.25
)


# --------------------------------------------------
# 9. Title
# --------------------------------------------------

fig.suptitle(
    "Brown Pelican Migration Rhythm",
    fontsize=22,
    weight="bold",
    y=0.96
)

fig.text(
    0.5,
    0.915,
    "Daily movement through the year",
    ha="center",
    fontsize=12
)


# --------------------------------------------------
# 10. Explanation
# --------------------------------------------------

fig.text(
    0.5,
    0.055,
    "CLOCKWISE = TIME THROUGH THE YEAR   •   DISTANCE FROM CENTRE = MEDIAN DAILY MOVEMENT",
    ha="center",
    fontsize=9
)

fig.text(
    0.5,
    0.028,
    "Based on GPS tracking records of Brown Pelicans",
    ha="center",
    fontsize=8
)


# --------------------------------------------------
# 11. Save
# --------------------------------------------------

os.makedirs(
    "out",
    exist_ok=True
)

plt.savefig(
    "out/migration_plot.png",
    dpi=300,
    bbox_inches="tight",
    facecolor=fig.get_facecolor()
)

plt.show()