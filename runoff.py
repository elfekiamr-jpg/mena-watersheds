"""
runoff.py

Adds curve-number-based runoff potential to a delineated watershed.
Sibling to morphology.py — same calling convention, meant to be invoked
from app.py right alongside compute_morphology().

WHAT THIS DOES
--------------
`delineate()` (from the `delineator` package) returns `watershed_gdf`: a
single dissolved polygon for the upstream watershed. It does NOT expose
which individual MERIT-Basins unit catchments (COMIDs) made up that
polygon, so to get an area-weighted curve number for the whole basin, we
spatially join our enriched catchment table (built in the manabi-data
pipeline) against that polygon ourselves.

Each candidate catchment's CENTROID (not full-polygon overlap) is tested
for containment within the watershed polygon. This is deliberate: since
watershed_gdf is built by dissolving a specific subset of the exact same
MERIT-Basins unit catchments our enriched table comes from, a catchment
either belongs to the basin or it doesn't — there's no meaningful partial
membership. Centroid-within is a fast, robust way to get that same
subset back, and it's not thrown off by the boundary simplification the
app applies for map rendering (DEFAULT_CONFIG has simplify=True), which
can distort exact polygon edges by a few dozen meters without changing
which catchments are really "in" the basin.

WHAT THIS DOESN'T DO (yet)
---------------------------
Rainfall intensity / IDF lookups. That needs the PXR-4 parameter
formula confirmed from the source file's own metadata before it's
implemented — see the accompanying TODO and don't guess at it.
"""

import logging
from pathlib import Path

import geopandas as gpd

logger = logging.getLogger(__name__)

# Path to the enriched catchment table published in manabi-data/data.
# For local dev, point this at a downloaded copy; in production this
# would be fetched from the public manabi-data repo at deploy/build time
# (see the raw.githubusercontent.com URL pattern from the data pipeline
# README) rather than bundled directly into this app's repo.
ENRICHED_CATCHMENTS_PATH = Path(__file__).parent / "data" / "enriched_catchments_egypt.parquet"

_enriched_catchments_cache = None


def _load_enriched_catchments() -> gpd.GeoDataFrame:
    """Load once, cache in memory for the life of the process."""
    global _enriched_catchments_cache
    if _enriched_catchments_cache is None:
        if not ENRICHED_CATCHMENTS_PATH.exists():
            raise FileNotFoundError(
                f"Enriched catchment table not found at {ENRICHED_CATCHMENTS_PATH}. "
                "Download it from manabi-data/data and place it there, or update "
                "ENRICHED_CATCHMENTS_PATH."
            )
        logger.info("Loading enriched catchment table from %s ...", ENRICHED_CATCHMENTS_PATH)
        gdf = gpd.read_parquet(ENRICHED_CATCHMENTS_PATH)
        # Precompute centroids once at load time rather than per-request —
        # this table doesn't change at runtime, so there's no reason to
        # redo this work on every delineation call.
        gdf["_centroid"] = gdf.geometry.centroid
        _enriched_catchments_cache = gdf
        logger.info("Loaded %d enriched catchments.", len(gdf))
    return _enriched_catchments_cache


def compute_runoff_potential(watershed_gdf: gpd.GeoDataFrame) -> dict | None:
    """
    Given the watershed polygon delineate() returns, find which enriched
    catchments fall inside it and compute an area-weighted curve number
    for dry/average/wet antecedent moisture conditions.

    Returns None if no enriched catchments matched (e.g. a click outside
    the region the enriched table currently covers — expected for now
    since only Egypt/basin 17 is built; will need updating as more
    megabasins are added to the enriched table).
    """
    catchments = _load_enriched_catchments()

    basin_geom = watershed_gdf.geometry.iloc[0]

    # Fast bounding-box prefilter before the real containment test —
    # matters once this table covers many megabasins, not just one.
    minx, miny, maxx, maxy = basin_geom.bounds
    bbox_candidates = catchments.cx[minx:maxx, miny:maxy]

    if len(bbox_candidates) == 0:
        logger.warning("No enriched catchments in bounding box of delineated watershed.")
        return None

    within_mask = bbox_candidates["_centroid"].within(basin_geom)
    matched = bbox_candidates[within_mask]

    if len(matched) == 0:
        logger.warning("No enriched catchments matched inside delineated watershed polygon.")
        return None

    total_area = matched["area_km2"].sum()
    if total_area == 0:
        return None

    def area_weighted(col: str) -> float:
        return float((matched[col] * matched["area_km2"]).sum() / total_area)

    return {
        "matched_catchments": int(len(matched)),
        "matched_area_km2": round(total_area, 2),
        "CN_dry": round(area_weighted("CN_dry"), 1),
        "CN_avg": round(area_weighted("CN_avg"), 1),
        "CN_wet": round(area_weighted("CN_wet"), 1),
        # IDF params carried through for the rainfall-intensity step —
        # not yet used to compute an actual intensity value (see TODO
        # in this module's docstring: formula needs confirming from
        # the PXR-4 file's own metadata before it's implemented).
        "_pxr_a": round(area_weighted("pxr_a"), 4),
        "_pxr_alpha": round(area_weighted("pxr_alpha"), 4),
        "_pxr_b": round(area_weighted("pxr_b"), 4),
        "_pxr_beta": round(area_weighted("pxr_beta"), 4),
    }
