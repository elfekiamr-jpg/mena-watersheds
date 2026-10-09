# Deploying to Vercel

## How the Vercel build works

`vercel.json` deploys two things:

- `index.html`: the map, served as a static file.
- `api/index.py`: a lightweight Flask app with **no `delineator`/geopandas/rasterio
  dependency**. For each click it calls mghydro.com's live, global watershed and
  upstream-rivers APIs, then computes morphology and builds the PDF report itself.

`app.py`, `predownload.py` and the other local-delineation files are excluded by
`.vercelignore`. They're for the Docker/VPS path in DEPLOY.md, which runs
`delineator` against downloaded MERIT data. That data is 1–3 GB per megabasin,
far too big for a Vercel function, so the Vercel build never touches it.

The tradeoff: this build depends on mghydro.com staying up and reachable.

## Coverage

Clicks are limited to the Middle East & North Africa: Morocco/Mauritania to Iran,
Turkey to Yemen/Sudan, with a small buffer. The box is
`MENA_BBOX = (-17.5, 8.5, 63.5, 42.5)` (lon_min, lat_min, lon_max, lat_max) in
`api/index.py`, which rejects anything outside it with a friendly message.
`MENA_BOUNDS` in `index.html` mirrors it, so out-of-area clicks are caught in the
browser before any request is sent. Keep the two in sync.

## Timeouts and resolution

`vercel.json` gives the function a **60-second `maxDuration`**, set in the
`@vercel/python` build's `config`. (The `functions` key can't be combined with
`builds`, so it lives there instead.) Check that your Vercel plan allows 60s.

Within that budget, `/api/delineate`:

1. Starts the upstream-rivers request in the background (up to 40s).
2. Requests the watershed at `precision=high` (up to 20s).
3. If that times out or fails, retries at `precision=low` (up to 25s). The response
   then carries `"precision": "low"` and the result panel shows a short
   "low-resolution boundary" note.

Worst case is about 45s plus processing. Large transboundary basins (a click on the
Nile, Tigris–Euphrates or a big Caspian river near its mouth) are the ones most
likely to fall back to low resolution.

## Runoff features are switched off

This build does delineation and morphology only. The GIUH (geomorphological unit
hydrograph) counts as morphology and stays on, in both the result panel and the PDF.
The runoff features (the "Runoff group" map overlay, plus the hydrologic soil group
map and composite curve number sections of the PDF report) are still in the code but
disabled by `RUNOFF_ENABLED = False` in **both** `api/index.py` and `index.html`. Set
both to `True` to bring them back.

## Place names and fonts

Place names come from OSM Nominatim with `accept-language=en`. Many MENA villages
and rural districts only have an Arabic or Persian name in OSM, so the report uses
the most specific address part that has an English name (e.g. the county). It falls
back to the local name only if none does. Non-Latin text in the PDF is drawn in
DejaVu Sans (bundled in `api/fonts/`, included via `includeFiles` in `vercel.json`),
shaped and ordered right-to-left by `arabic-reshaper` and `python-bidi`.

## Steps

1. **Push this repo to GitHub.**
2. **On vercel.com:** Add New… → Project → import the repo.
3. **Deploy.** Vercel installs `api/requirements.txt` (Flask, flask-cors,
   reportlab; no heavy geo libraries) and routes `/api/*` to `api/index.py`.
   Everything else goes to `index.html`.
4. You get a live `*.vercel.app` URL.

## Likely failure points

- **"Server error" toasts on big basins.** If mghydro.com is slow even at low
  precision, the low-res retry can still fail. Check the function logs in Vercel.
  If it's frequent, raise `maxDuration` (plan permitting) and the timeouts in
  `api/index.py`'s `delineate()`.
- **The build ignores `maxDuration`.** Check the function's configured duration in
  the Vercel dashboard after the first deploy. If it isn't 60s, switch
  `vercel.json` from `builds`/`routes` to `functions`/`rewrites`.
- **JSON-shape errors from the proxy.** mghydro.com's API shape isn't controlled by
  this repo. Check that `watershed_data.get('features')` in `delineate()` still
  matches what it returns.
