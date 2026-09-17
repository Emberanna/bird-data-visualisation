import json
import math
import os
import numpy as np
import matplotlib.pyplot as plt


INPUT = "data/gbif-bird-observations.json"
OUTPUT = "out/ripple.png"


def load_species():

    species_count = {}

    with open(INPUT, encoding="utf-8") as f:
        data = json.load(f)

    for row in data["results"]:

        name = (
            row.get("species")
            or row.get("scientificName")
            or row.get("genus")
            or "Unknown"
        )

        species_count[name] = (
            species_count.get(name, 0) + 1
        )


    top_species = sorted(
        species_count.items(),
        key=lambda x: x[1],
        reverse=True
    )[:10]


    return top_species



def draw_ripple(species):

    fig, ax = plt.subplots(
        figsize=(8, 8)
    )


    ax.set_aspect("equal")
    ax.axis("off")


    fig.patch.set_facecolor("#faf8f3")
    ax.set_facecolor("#faf8f3")


    colors = plt.cm.rainbow(
        np.linspace(
            0,
            1,
            len(species)
        )
    )


    max_value = max(
        value for _, value in species
    )


    for i, ((name, count), color) in enumerate(
        zip(species, colors)
    ):


        radius = 0.8 + i * 0.35


        theta = np.linspace(
            0,
            math.pi * 2,
            400
        )


        strength = count / max_value


        distortion = (
            np.sin(theta * (i + 3))
            * 0.05
            * strength
        )


        r = radius + distortion


        x = r * np.cos(theta)
        y = r * np.sin(theta)


        ax.plot(
            x,
            y,
            color=color,
            linewidth=2,
            alpha=0.85
        )


        ax.text(
            0,
            radius + 0.08,
            name[:20],
            fontsize=8,
            ha="center",
            color="#333333"
        )


    ax.scatter(
        0,
        0,
        s=50,
        color="#222222"
    )


    ax.set_title(
        "Bird Species Ripple",
        fontsize=18,
        pad=25
    )


    os.makedirs(
        "out",
        exist_ok=True
    )


    plt.savefig(
        OUTPUT,
        dpi=300,
        bbox_inches="tight"
    )


    plt.close()



def main():

    species = load_species()

    draw_ripple(species)

    print(
        "Saved:",
        OUTPUT
    )



if __name__ == "__main__":
    main()