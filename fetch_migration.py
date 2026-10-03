# /// script
# requires-python = ">=3.10,<3.14"
# dependencies = [
#     "pandas",
# ]
# ///
import pandas as pd

# Load the two original datasets
stork = pd.read_csv("data/White Stork Adults 2017_part.csv")
pelican = pd.read_csv("data/Brown pelican data from Lamb et al. (2017).csv")

# Keep the migration fields we need
columns = [
    "timestamp",
    "location-long",
    "location-lat",
    "individual-local-identifier"
]

stork_clean = stork[columns].copy()
pelican_clean = pelican[columns].copy()

# Add species names
stork_clean["species"] = "White Stork"
pelican_clean["species"] = "Brown Pelican"

# Combine the two species
migration = pd.concat(
    [stork_clean, pelican_clean],
    ignore_index=True
)

# Rename columns to make them easier to use
migration = migration.rename(columns={
    "location-long": "longitude",
    "location-lat": "latitude",
    "individual-local-identifier": "bird_id"
})

# Remove rows without location or time
migration = migration.dropna(
    subset=["timestamp", "longitude", "latitude"]
)
# Remove impossible GPS coordinates
migration = migration[
    migration["longitude"].between(-180, 180)
    & migration["latitude"].between(-90, 90)
]
# Save the cleaned dataset
migration.to_csv(
    "data/migration-data.csv",
    index=False
)

print("Migration data created!")
print("Total rows:", len(migration))
print("\nRows by species:")
print(migration["species"].value_counts())