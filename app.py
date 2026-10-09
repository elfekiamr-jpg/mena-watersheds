"""
MENA Watersheds — backend (Docker/VPS path)

A thin Flask wrapper around the open-source `delineator` package
(https://pypi.org/project/delineator/, MIT licensed, by Matthew Heberger),
restricted to the Middle East & North Africa.

MENA spans nine Pfafstetter level-2 megabasins: 11, 14, 15, 16, 17, 21, 22,
28 and 29 (see README.md for what each covers). `delineator` auto-detects the
megabasin from the clicked point and downloads *only that basin's* data files
(1-3 GB each) the first time it's needed.

Run:
    pip install -r requirements.txt
    python app.py
Then open http://127.0.0.1:5000
"""

import json
import logging
import traceback

from flask import Flask, Response, jsonify, request, send_from_directory

import data_dir  # noqa: F401  (sets DELINEATOR_DATA_DIR before delineator loads)
import vercel_numba_fix  # noqa: F401  (must come before numba is imported — see file)
import vercel_skimage_fix  # noqa: F401  (harmless no-op outside Vercel — see file for why)
from delineator.core import delineate
from delineator.settings import DelineatorConfig
from morphology import compute_morphology

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder="static", static_url_path="")

# MENA bounding box: Morocco/Mauritania to Iran, Turkey to Yemen/Sudan, plus a
# small buffer. Matches MENA_BBOX in api/index.py and MENA_BOUNDS in index.html.
# (lon_min, lat_min, lon_max, lat_max)
MENA_BBOX = (-17.5, 8.5, 63.5, 42.5)

# A sane default for interactive use: rivers + outlets returned, results
# cached per session so re-clicking near the same stream is instant, and
# the boundary is cleaned/simplified so it renders nicely on a web map.
DEFAULT_CONFIG = DelineatorConfig(
    high_res=True,
    rivers=True,
    outlets=True,
    clean=True,
    simplify=True,
    cache=True,
)


def _in_mena_bbox(lat: float, lng: float) -> bool:
    lon_min, lat_min, lon_max, lat_max = MENA_BBOX
    return lon_min <= lng <= lon_max and lat_min <= lat <= lat_max


@app.route("/")
def index() -> Response:
    return send_from_directory("static", "index.html")


@app.route("/api/delineate", methods=["POST"])
def delineate_endpoint() -> Response:
    body = request.get_json(silent=True) or {}
    lat, lng = body.get("lat"), body.get("lng")
    mode = body.get("mode", "up")

    if lat is None or lng is None:
        return jsonify({"error": "Request body must include 'lat' and 'lng'."}), 400

    if mode == "down":
        # The `delineator` package (as of 2.2.4) only does upstream watershed
        # delineation, not downstream flow-path tracing like the original
        # mghydro.com/watersheds app. Building that would mean walking the
        # flow-direction raster (flowdir29.tif) yourself with pysheds, which
        # is already a dependency here — a good follow-up, not in this MVP.
        return jsonify({
            "error": "Downstream flow-path tracing isn't implemented yet in this build."
        }), 501

    try:
        lat, lng = float(lat), float(lng)
    except (TypeError, ValueError):
        return jsonify({"error": "'lat' and 'lng' must be numeric."}), 400

    if not _in_mena_bbox(lat, lng):
        return jsonify({
            "error": "That point is outside the Middle East & North Africa. "
                     "This tool covers Morocco to Iran and Turkey to Yemen/Sudan."
        }), 400

    logger.info("Delineating watershed at lat=%.4f, lng=%.4f", lat, lng)

    try:
        watershed_gdf, rivers_gdf, outlets_gdf = delineate(lat, lng, config=DEFAULT_CONFIG)
    except Exception:
        logger.error(traceback.format_exc())
        return jsonify({"error": "Delineation failed. See server logs for details."}), 500

    if watershed_gdf is None:
        return jsonify({
            "error": "Could not delineate a watershed there. Make sure the point "
                     "is over land and on/near a mapped stream."
        }), 422

    def to_geojson(gdf):
        return None if gdf is None else json.loads(gdf.to_json())

    try:
        morphology = compute_morphology(watershed_gdf, rivers_gdf, lat, lng)
    except Exception:
        # Don't let a morphology calculation bug break the whole request —
        # the watershed/rivers/outlets are still useful without it.
        logger.error("Morphology calculation failed:\n%s", traceback.format_exc())
        morphology = None

    return jsonify({
        "watershed": to_geojson(watershed_gdf),
        "rivers": to_geojson(rivers_gdf),
        "outlets": to_geojson(outlets_gdf),
        "morphology": morphology,
    })


if __name__ == "__main__":
    print("\n  MENA Watersheds — local dev server")
    print("  -----------------------------------")
    print("  Open http://127.0.0.1:5000 in your browser")
    print("  Each click auto-downloads its megabasin's data the first time")
    print("  (1-3 GB per megabasin — see README)\n")
    app.run(host="127.0.0.1", port=5000, debug=False, use_reloader=False, threaded=True)
