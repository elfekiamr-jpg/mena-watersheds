# Plan: extend the Egypt watershed app to MENA

Scope: Morocco to Iran, Turkey to Yemen/Sudan.

**Key finding:** the Vercel app doesn't use any local MERIT data. `api/index.py` (the only thing Vercel deploys) sends each click to mghydro.com's global watershed API (`api/index.py:2928`). The local `delineator` setup with downloaded megabasins is only used by `app.py`, the Docker/VPS version, and `.vercelignore` leaves it out of the Vercel bundle. So the deployed app can already delineate anywhere in MENA; what's missing is the map view, the bounds and the labels.

## 1. Megabasins needed for MENA

About 90 points across the region were looked up in delineator's own `megabasins.db`. These are spot checks at cities and border areas, not a full country-by-country overlay.

| Basin | Covers | Status |
|---|---|---|
| 15 | All of the Maghreb, Libya, northern Mauritania, Western Desert | have |
| 17 | Nile: Egypt and most of Sudan, including Khartoum, Darfur east and Kassala | have |
| 11 | Red Sea west coast: Port Sudan, Eritrea, Djibouti, Socotra | have |
| 21 | Mediterranean coast: Levant coast, western and southern Turkey, Thrace, Cyprus | have |
| 29 | Arabia, Iraq, inland Syria and Jordan, eastern Turkey, most of Iran, Yemen, Oman, Gulf | have |
| **22** | Central and northern Anatolia, Turkey's Black Sea coast (Konya, Ankara, Samsun, Trabzon) | **new** |
| **28** | Caspian drainage: northern Iran (Tabriz, Rasht, Mashhad), Kars | **new** |
| **16** | Lake Chad: western Darfur (Geneina), SE Algeria (Djanet) | **new** |
| **14** | Niger: far southern Algeria (Tin Zaouaten), southern Mauritania | **new** |

Basins 23 and 46 touch the edges of the bounding box, but none of the MENA test points fell in them.

## 2. Where coverage, map view, bounds and Egypt labels live

**Frontend (`index.html`):**
- Line 6: `<title>` is "Manabi — Egypt Watersheds".
- Line 265: the heading "Watersheds of Egypt".
- Line 315: the footer text that lists basins 17/29/15/21/11.
- Lines 323–330: `EGYPT_BOUNDS` (defined but never used), `EGYPT_CENTER`, `setView(…, 6)`, `minZoom: 4`, and `maxBounds: [[15,18],[38,44]]`. The `maxBounds` setting stops people panning to Morocco or Iran, so it needs widening to roughly `[[5,-20],[45,66]]`, centered near `[28,22]` at zoom 4, with `minZoom` 3.
- Line 786: the click handler. It sends every click straight to the backend with no bounds check.

**Backend (Vercel):**
- `api/index.py:1941`: PDF footer, "…watershed delineation for Egypt".
- `api/index.py:3059`: catch-all message, "Egypt Watersheds API active".
- `api/morphology_lite.py:256`: the same message, in what looks like a leftover copy.
- There's no coverage check here at all. Adding a MENA bounding-box check is optional.

**Docker/VPS only:**
- `app.py`: `EGYPT_BBOX`, `_in_egypt_bbox`, the error text and the docstring.
- `predownload.py`: `BASINS_TO_PREFETCH`.
- `docker-compose.yml`: the `egypt_data` volume.
- `runoff.py:47,81`: an Egypt-only calibration file, `enriched_catchments_egypt.parquet`.

**Docs:** `README.md`, `DEPLOY.md` and `VERCEL_DEPLOY.md`. Also, `VERCEL_DEPLOY.md` says `vercel.json` sets a 30s `maxDuration`, but `vercel.json` doesn't set one.

## 3. MERIT data as GitHub Release assets, loaded per megabasin

**Recommendation: don't do this on Vercel.** Real file sizes on mghydro:

- Each megabasin is **1.0–3.3 GB**. The largest single file is `basins15.db` at 1.47 GB.
- All nine basins add up to about **17 GB**. Even low-res, which only needs the `.db` files, is about **8.4 GB**.
- A Vercel function can only write to `/tmp`, which holds about 500 MB, so it can't fit even one basin. Downloading gigabytes on each click would also blow past any timeout.

GitHub Releases could store the files, since each one is under the 2 GB per-file limit. Vercel just can't use them.

What to do instead:
- **Vercel:** keep using the mghydro API proxy. The MENA work is then frontend, label and bounds changes plus item 4.
- **To stop depending on mghydro:** use the Docker/VPS path (`app.py`) on a server with about 20 GB of disk. `delineator` already downloads only the basin that was clicked, the first time it's needed. A GitHub Release copy would only be useful as a backup download source there.

## 4. Low-res by default to avoid timeouts?

On the Vercel path, the relevant setting is mghydro's `precision=high` in `api/index.py:2928`. The function makes two calls in a row, each with a 25s timeout, so one click can take up to about 50s. Big basins like the Nile, Tigris–Euphrates or the Caspian rivers are the ones likely to time out.

Recommendation:
- Try `precision=high` with a shorter timeout. If it times out, retry automatically with `precision=low`, and show a small "low-res" note in the result panel.
- Set `maxDuration` explicitly in `vercel.json` (for example 60) and check that the Vercel plan allows that limit.

Making low-res the only mode would cost accuracy for the small catchments where most clicks land. In the Docker path the same idea is `high_res=False`, which also skips the large raster files.

## Order of work

1. `index.html` bounds and labels.
2. Backend labels and an optional MENA bounding-box check.
3. The precision fallback and `maxDuration`.
4. The docs.
