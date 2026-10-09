# Deploying as a real website (Docker/VPS)

This is the self-hosted path, which runs `delineator` locally. The main deployment
is Vercel (see VERCEL_DEPLOY.md), which needs no local data.

## Pick a host

The app needs a real VPS (not a bare static host), since it runs Python +
geopandas/rasterio and stores MERIT hydrology data on disk.

**Disk is the main constraint.** MENA spans nine megabasins (11, 14, 15, 16, 17,
21, 22, 28, 29; see README.md). Their full data, measured on mghydro.com, is
1.0–3.3 GB per basin and about **17 GB** in total. Each basin downloads the first
time a click lands in it, so plan for all of it. Starting points:

- **Hetzner Cloud CX22**: 2 vCPU / 4 GB RAM / 40 GB disk, ~€4.6/month.
- **DigitalOcean Basic Droplet**: 2 GB RAM / 50 GB disk, $12/month.

Avoid free-tier PaaS (Render/Railway free, Heroku free): 512 MB RAM is too tight
for these spatial indexes.

You'll also want a domain (or subdomain) pointed at the server — any
registrar works, you just need an **A record** aiming at the VPS's IP.

## One-time server setup

SSH into the fresh VPS, then:

```bash
# Install Docker + Compose plugin (Ubuntu/Debian)
curl -fsSL https://get.docker.com | sh
apt-get install -y docker-compose-plugin
```

## Deploy

```bash
# From your machine: copy the project to the server
scp -r eg-watersheds root@YOUR_SERVER_IP:/root/

# On the server
cd /root/eg-watersheds
```

Edit `Caddyfile` and replace `your-domain.com` with your actual domain —
Caddy uses this to request a free Let's Encrypt certificate automatically
on first boot. Then:

```bash
docker compose up -d --build
```

The build step downloads megabasin 17's data (unit catchments, rivers,
flow direction, flow accumulation for the whole Nile Basin) into the
image — this is the slow part, and likely slower than KSA's build was.
Give it real time depending on file size and your connection. Once it's
up, visit `https://your-domain.com` — Caddy handles HTTPS for you, no
certbot/nginx config needed.

Clicks in the other MENA megabasins aren't baked into the image. They download
on first click instead, and persist across restarts in the `mena_data` Docker
volume that's already wired up in `docker-compose.yml`.

## After deploying

```bash
docker compose logs -f app       # tail the app's logs
docker compose restart app       # restart just the app
docker compose down && docker compose up -d --build   # rebuild after code changes
```

Since basin 17's data is baked into the image, redeploys after a *code*
change (editing `app.py` or `index.html`) will re-run the data download
step too unless you reorder the Dockerfile so `COPY app.py .` / `COPY
static/` come after the `RUN downloader(17)` line — they already do in the
Dockerfile provided, so Docker's layer cache will skip re-downloading as
long as `requirements.txt` hasn't changed.

## Costs to expect

- VPS: ~€4.60–$12/month, with at least 40 GB disk for all of MENA's data
- Domain: ~$10–15/year if you don't already have one
- Data transfer/bandwidth: negligible at portfolio-project traffic levels
