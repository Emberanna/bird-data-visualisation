# /// script
# requires-python = ">=3.10"
# dependencies = ["matplotlib"]
# ///

import json
import math
from pathlib import Path

import matplotlib.pyplot as plt


FILE = "gbif-bird-observations.json"

HERE = Path(__file__).parent
DATA = HERE / "data" / FILE
OUT = HERE / "out"


def rows(path):
    with path.open(encoding="utf-8") as f:
        data = json.load(f)

    return data["results"]



def main():

    table = rows(DATA)

    counts = {}

    for row in table:
        species = row.get("species")

        if species:
            counts[species] = counts.get(species, 0) + 1


    top_species = sorted(
        counts.items(),
        key=lambda x:x[1],
        reverse=True
    )[:10]


    print(top_species)


    fig, ax = plt.subplots(
        figsize=(10,10)
    )


    # background
    ax.set_facecolor("#faf8f2")


    max_value = top_species[0][1]


    for index,(name,value) in enumerate(top_species):

        angle = index * (360/len(top_species))

        x = math.cos(math.radians(angle))*2
        y = math.sin(math.radians(angle))*2


        # ring size controlled by observation number
        radius = 0.25 + value/max_value*0.5


        # multiple ripple circles
        for i in range(5):

            r = radius*(i+1)/5


            circle = plt.Circle(
                (x,y),
                r,
                fill=False,
                linewidth=1.2,
                alpha=0.6
            )

            ax.add_patch(circle)



        # bird name inside ring

        ax.text(
            x,
            y,
            name.replace(" ","\n"),
            ha="center",
            va="center",
            fontsize=8
        )


        # number below

        ax.text(
            x,
            y-radius-0.15,
            f"{value} records",
            ha="center",
            fontsize=7
        )


    # center title

    ax.text(
        0,
        0,
        "GBIF\nBird\nObservations",
        ha="center",
        va="center",
        fontsize=12
    )


    ax.set_xlim(-3,3)
    ax.set_ylim(-3,3)

    ax.axis("off")


    plt.title(
        "Bird Species Ripple Map\n300 GBIF Occurrence Records",
        fontsize=16
    )


    OUT.mkdir(exist_ok=True)

    plt.savefig(
        OUT/"plot.png",
        dpi=150,
        bbox_inches="tight"
    )


    plt.show()



if __name__=="__main__":
    main()