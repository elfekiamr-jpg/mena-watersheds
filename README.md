# Manabi (منابع) — MENA Watersheds

A Middle East & North Africa–scoped clone of [mghydro.com/watersheds](https://mghydro.com/watersheds):
click a point anywhere from Morocco to Iran, or from Turkey to Yemen/Sudan, to trace
its upstream watershed. It also computes morphology parameters and can build a PDF
report.

It grew out of the Egypt build of Manabi (itself a sibling of the Saudi Arabia
build). This build does **delineation only**. The runoff features (hydrologic soil
group, composite curve number, GIUH) are still in the code but switched off with
`RUNOFF_ENABLED`. See VERCEL_DEPLOY.md.

## Two ways to run it

| | Vercel (main) | Docker / VPS |
|---|---|---|
| Code | `index.html` + `api/index.py` | `app.py` + `static/` |
| Delineation | Proxies mghydro.com's live global API | Local [`delineator`](https://pypi.org/project/delineator/) package against downloaded MERIT data |
| Data on disk | None | 1–3 GB per megabasin, about 17 GB for all of MENA |
| Guide | VERCEL_DEPLOY.md | DEPLOY.md |

Both restrict clicks to the same MENA bounding box,
`(-17.5, 8.5, 63.5, 42.5)` (lon_min, lat_min, lon_max, lat_max), and reject
points outside it with a friendly message.

## Megabasins covering MENA

These were found by checking points across the region against `delineator`'s
`megabasins.db`. They matter for the Docker/VPS path, which downloads each basin's
data the first time a click lands in it.

| Basin | Covers | Full data size |
|---|---|---|
| 15 | The Maghreb, Libya, northern Mauritania, Egypt's Western Desert | 3.3 GB |
| 17 | The Nile: Egypt and most of Sudan, and upstream to Ethiopia and Lake Victoria | 1.7 GB |
| 11 | Red Sea west coast: Port Sudan, Eritrea, Djibouti, Socotra | 1.6 GB |
| 21 | Mediterranean coast: Levant coast, western and southern Turkey, Thrace, Cyprus | 1.0 GB |
| 29 | Arabia, Iraq, inland Syria and Jordan, eastern Turkey, most of Iran, Yemen, Oman, the Gulf | 2.7 GB |
| 22 | Central and northern Anatolia, Turkey's Black Sea coast | 1.7 GB |
| 28 | Caspian drainage: northern Iran, Kars | 2.6 GB |
| 16 | Lake Chad: western Darfur, SE Algeria | 1.3 GB |
| 14 | Niger: far southern Algeria, southern Mauritania | 1.8 GB |

Low-resolution delineation (`high_res=False`) only needs each basin's `.db` files,
about 8.4 GB for all nine.

**Transboundary rivers:** a click on the Nile, Tigris–Euphrates or another large
river traces the true upstream watershed, which can span many countries. That's
correct hydrology, not a bug.

## Local setup (Docker/VPS code path)

```bash
python -m venv venv
source venv/bin/activate       # venv\Scripts\activate on Windows
pip install -r requirements.txt
python app.py
```

Open http://127.0.0.1:5000. The first click in each megabasin downloads that
basin's data. `python predownload.py` pre-fetches the basins listed in
`BASINS_TO_PREFETCH`.

## What's implemented

- Click-to-delineate upstream watershed, with river network and outlet points
- Snapped-outlet coordinates, drainage area and morphology parameters
- GeoJSON, KML and PDF report downloads
- Land-cover and soil-type map overlays
- On Vercel: high-resolution delineation with an automatic low-resolution fallback
  for large basins

## Not (yet) implemented

- **Downstream flow-path tracing.** `delineator` only does upstream watersheds.
- **Runoff** (switched off for this build; see above).
- **Arabic UI.** The header carries an Arabic label (منابع); a full RTL pass would
  suit the audience.

## Credit

Delineation: MERIT-Hydro (Yamazaki et al.) and MERIT-Basins (Lin et al.), via
mghydro.com's API and the `delineator` package by Matthew Heberger (MIT license).
This project is an independent frontend/scoping layer, not affiliated with
mghydro.com.
