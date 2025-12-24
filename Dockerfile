FROM jrottenberg/ffmpeg:4.4-alpine

USER root

# Install system dependencies for Pillow and Python
RUN apk add --no-cache \
    python3 \
    py3-pip \
    wget \
    curl \
    fontconfig \
    ttf-dejavu \
    ttf-liberation \
    font-noto \
    jpeg-dev \
    zlib-dev \
    freetype-dev \
    lcms2-dev \
    openjpeg-dev \
    tiff-dev \
    tk-dev \
    tcl-dev \
    harfbuzz-dev \
    fribidi-dev \
    libimagequant-dev \
    libxcb-dev \
    libpng-dev \
    gcc \
    musl-dev \
    python3-dev

# Font cache
RUN fc-cache -fv

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "900", "app:app"]
