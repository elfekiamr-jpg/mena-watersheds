import os

import data_dir  # sets DELINEATOR_DATA_DIR to a path next to this file

os.makedirs(data_dir.DATA_DIR, exist_ok=True)

from delineator.core import downloader  # noqa: E402

# MENA spans nine megabasins (see README.md for what each one covers and
# its size, 1-3 GB each). Only basin 17, the Nile, is pre-fetched by
# default; the rest auto-download on first click. Uncomment below to bake
# in all of MENA (~17 GB).
BASINS_TO_PREFETCH = [17]
# BASINS_TO_PREFETCH = [11, 14, 15, 16, 17, 21, 22, 28, 29]  # all of MENA, baked in

for basin in BASINS_TO_PREFETCH:
    print(f"Downloading megabasin {basin} data to {data_dir.DATA_DIR} ...")
    downloader(basin)

print("Done.")
