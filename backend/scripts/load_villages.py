import os
import zipfile
import shutil
from pathlib import Path

import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text


# ============================================================
# PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parents[1]

DATA_DIR = BASE_DIR / "data"
VILLAGE_DIR = DATA_DIR / "village_boundaries"

ZIP_FILE = VILLAGE_DIR / "UTTARAKHAND.zip"
EXTRACT_DIR = VILLAGE_DIR / "uttarakhand_extracted"


# ============================================================
# DATABASE
# ============================================================

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://postgres:Avanee%40postgre@localhost:5432/chamoli_flood"
)

engine = create_engine(DATABASE_URL)


# ============================================================
# HELPERS
# ============================================================

def find_shapefile():
    """Find the first shapefile inside the extracted directory."""

    shp_files = list(EXTRACT_DIR.rglob("*.shp"))

    if not shp_files:
        raise FileNotFoundError(
            f"No .shp file found inside {EXTRACT_DIR}"
        )

    print("\nShapefile found:")
    print(shp_files[0])

    return shp_files[0]


def find_column(columns, keywords):
    """
    Find a likely column from a list of keywords.
    """

    normalized = {
        str(col).lower().replace(" ", "_").replace("-", "_"): col
        for col in columns
    }

    # Exact matches first
    for keyword in keywords:
        key = keyword.lower().replace(" ", "_").replace("-", "_")

        if key in normalized:
            return normalized[key]

    # Partial matches
    for normalized_name, original_name in normalized.items():

        for keyword in keywords:

            keyword = keyword.lower().replace(" ", "_").replace("-", "_")

            if keyword in normalized_name:
                return original_name

    return None


# ============================================================
# EXTRACT
# ============================================================

def extract_zip():

    if not ZIP_FILE.exists():
        raise FileNotFoundError(
            f"\nVillage boundary ZIP not found:\n{ZIP_FILE}\n\n"
            "Download the official Uttarakhand village boundary ZIP "
            "and place it in backend/data/village_boundaries/"
        )

    if EXTRACT_DIR.exists():
        print("Existing extraction found. Reusing it.")

    else:
        print("\nExtracting Uttarakhand village boundaries...")

        EXTRACT_DIR.mkdir(
            parents=True,
            exist_ok=True
        )

        with zipfile.ZipFile(ZIP_FILE, "r") as zip_ref:
            zip_ref.extractall(EXTRACT_DIR)

    print("Extraction complete.")


# ============================================================
# LOAD SHAPEFILE
# ============================================================

def load_boundaries():

    shp_file = find_shapefile()

    print("\nReading shapefile...")

    gdf = gpd.read_file(shp_file)

    print("\nOriginal columns:")
    print(list(gdf.columns))

    print("\nCRS:")
    print(gdf.crs)

    print("\nRows:")
    print(len(gdf))

    return gdf


# ============================================================
# IDENTIFY ADMINISTRATIVE COLUMNS
# ============================================================

def identify_columns(gdf):

    village_col = find_column(
        gdf.columns,
        [
            "village_name",
            "village",
            "vill_name",
            "vill_nm",
            "village_nm",
            "name",
        ],
    )

    district_col = find_column(
        gdf.columns,
        [
            "district_name",
            "district",
            "dist_name",
            "dist_nm",
            "district_nm",
        ],
    )

    block_col = find_column(
        gdf.columns,
        [
            "block_name",
            "block",
            "sub_dist",      # <--- Add this
            "subdistrict",
            "sub_district",
            "tehsil",
            "taluk",
        ],
    )

    gp_col = find_column(
        gdf.columns,
        [
            "gram_panchayat",
            "gram_panch",
            "panchayat",
            "gp_name",
        ],
    )

    print("\nDetected columns:")
    print("Village :", village_col)
    print("District:", district_col)
    print("Block   :", block_col)
    print("GP      :", gp_col)

    if village_col is None:
        raise RuntimeError(
            "\nCould not automatically identify the village-name column.\n"
            "Look at the 'Original columns' output and set village_col manually."
        )

    return village_col, district_col, block_col, gp_col


# ============================================================
# FILTER CHAMOLI
# ============================================================

def filter_chamoli(
    gdf,
    village_col,
    district_col,
    block_col,
    gp_col,
):

    if district_col is not None:

        print("\nDistrict values:")

        values = (
            gdf[district_col]
            .dropna()
            .astype(str)
            .drop_duplicates()
            .sort_values()
        )

        print(values.to_string(index=False))

        mask = (
            gdf[district_col]
            .astype(str)
            .str.strip()
            .str.lower()
            .str.contains("chamoli", na=False)
        )

        chamoli = gdf[mask].copy()

    else:

        print(
            "\nWARNING: District column was not detected."
        )

        chamoli = gdf.copy()

    print(
        f"\nChamoli village polygons: {len(chamoli):,}"
    )

    if len(chamoli) == 0:

        raise RuntimeError(
            "\nNo Chamoli polygons were found.\n"
            "Check the district field name and values."
        )

    return chamoli


# ============================================================
# PREPARE DATA
# ============================================================

def prepare_gdf(
    gdf,
    village_col,
    district_col,
    block_col,
    gp_col,
):

    result = gdf.copy()

    # WGS84 geographic CRS
    result = result.to_crs("EPSG:4326")

    # Rename fields to stable application names
    result["village_name"] = (
        result[village_col]
        .astype(str)
        .str.strip()
    )

    if district_col is not None:
        result["district_name"] = (
            result[district_col]
            .astype(str)
            .str.strip()
        )
    else:
        result["district_name"] = "Chamoli"

    if block_col is not None:
        result["block_name"] = (
            result[block_col]
            .astype(str)
            .str.strip()
        )
    else:
        result["block_name"] = None

    if gp_col is not None:
        result["gram_panchayat"] = (
            result[gp_col]
            .astype(str)
            .str.strip()
        )
    else:
        result["gram_panchayat"] = None

    # Remove empty geometries
    result = result[
        result.geometry.notna()
    ].copy()

    result = result[
        ~result.geometry.is_empty
    ].copy()

    # Keep only application fields
    result = result[
        [
            "village_name",
            "district_name",
            "block_name",
            "gram_panchayat",
            "geometry",
        ]
    ]

    # Fix invalid geometries where possible
    result["geometry"] = result.geometry.buffer(0)

    result = result.reset_index(drop=True)

    # Stable numeric ID
    result.insert(
        0,
        "village_id",
        range(1, len(result) + 1),
    )

    return result


# ============================================================
# WRITE TO POSTGIS
# ============================================================

def save_to_postgis(gdf):

    print(
        "\nWriting village boundaries to PostgreSQL/PostGIS..."
    )

    # Replace only this application table
    gdf.to_postgis(
        name="village_boundaries",
        con=engine,
        if_exists="replace",
        index=False,
    )

    print(
        "\nVillage boundary table created:"
    )

    print("    village_boundaries")


# ============================================================
# CREATE INDEXES
# ============================================================

def create_indexes():

    with engine.begin() as conn:

        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS
                idx_village_boundaries_geometry
                ON village_boundaries
                USING GIST (geometry);
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS
                idx_village_boundaries_name
                ON village_boundaries(village_name);
                """
            )
        )

        conn.execute(
            text(
                """
                CREATE INDEX IF NOT EXISTS
                idx_village_boundaries_district
                ON village_boundaries(district_name);
                """
            )
        )

    print("\nPostGIS indexes created.")


# ============================================================
# TEST
# ============================================================

def test_database():

    with engine.connect() as conn:

        count = conn.execute(
            text(
                """
                SELECT COUNT(*)
                FROM village_boundaries;
                """
            )
        ).scalar()

        print(
            f"\nVillage polygons in database: {count:,}"
        )

        rows = conn.execute(
            text(
                """
                SELECT
                    village_id,
                    village_name,
                    district_name,
                    block_name
                FROM village_boundaries
                ORDER BY village_name
                LIMIT 20;
                """
            )
        ).fetchall()

        print("\nSample villages:")

        for row in rows:
            print(row)


# ============================================================
# MAIN
# ============================================================

def main():

    print("=" * 70)
    print("CHAMOLI VILLAGE BOUNDARY IMPORT")
    print("=" * 70)

    extract_zip()

    gdf = load_boundaries()

    (
        village_col,
        district_col,
        block_col,
        gp_col,
    ) = identify_columns(gdf)

    chamoli = filter_chamoli(
        gdf,
        village_col,
        district_col,
        block_col,
        gp_col,
    )

    chamoli = prepare_gdf(
        chamoli,
        village_col,
        district_col,
        block_col,
        gp_col,
    )

    save_to_postgis(chamoli)

    create_indexes()

    test_database()

    print("\n" + "=" * 70)
    print("VILLAGE IMPORT COMPLETED")
    print("=" * 70)


if __name__ == "__main__":
    main()