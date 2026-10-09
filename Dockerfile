FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libexpat1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt gunicorn

# Bake megabasin 17 (the whole Nile Basin — the region almost every real
# click on this site will land in) into the image at build time. This is
# a much bigger download than KSA's single basin 29 was, since basin 17
# covers the entire transboundary Nile system (Sudan/Ethiopia/Uganda too,
# not just Egypt).
# The other MENA megabasins (11, 14, 15, 16, 21, 22, 28, 29) are NOT
# baked in here and will download on first click instead; add them to
# this RUN line (`downloader()` calls) to bake them in, at 1-3 GB each.
ENV DELINEATOR_DATA_DIR=/data
RUN mkdir -p /data && \
    python -c "from delineator.core import downloader; downloader(17)"

COPY app.py .
COPY data_dir.py .
COPY vercel_skimage_fix.py .
COPY vercel_numba_fix.py .
COPY static/ static/


EXPOSE 8000
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "2", "--threads", "4", "--timeout", "120", "app:app"]
