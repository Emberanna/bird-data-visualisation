# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///

"""
Read the GBIF bird observation data, make one picture, and save it to out/.

    uv run plot.py

The data contains bird occurrence records from GBIF.
This script counts how many records belong to each bird species
and plots the 10 most frequently recorded species.
"""

import json
from pathlib import Path

import matplotlib.pyplot as plt

FILE = "gbif-bird-observations.json"
PICTURE = "plot.png"

HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"


def rows(path):
    """Read the GBIF JSON file and return the occurrence records."""
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    return data["results"]


def main():
    table = rows(DATA)

    # Print the first row, one value, and its type before plotting.
    print(f"{DATA.name}: {len(table)} rows.")
    print("The first row:", table[0])
    print("One value:", table[0].get("species"))
    print("Type:", type(table[0].get("species")))

    # Count observations for each bird species.
    counts = {}

    for row in table:
        species = row.get("species")

        if species:
            counts[species] = counts.get(species, 0) + 1

    top_species = sorted(
        counts.items(),
        key=lambda item: item[1],
        reverse=True
    )[:10]

    names = [item[0] for item in top_species]
    values = [item[1] for item in top_species]

    print(f"{len(counts)} different species found.")
    print("Top 10 species:", top_species)

    # Make the picture.
    fig, ax = plt.subplots(figsize=(10, 6))

    ax.barh(names[::-1], values[::-1])

    ax.set_xlabel("Number of observations")
    ax.set_ylabel("Bird species")
    ax.set_title("Top 10 Bird Species in GBIF Occurrence Records")

    fig.tight_layout()

    OUT.mkdir(exist_ok=True)
    fig.savefig(OUT / PICTURE, dpi=150)

    print(f"saved out/{PICTURE}")

    plt.show()


if __name__ == "__main__":
    main()