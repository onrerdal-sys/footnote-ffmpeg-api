FROM jrottenberg/ffmpeg:4.4-alpine

USER root

# Install Python and dependencies
RUN apk add --no-cache \
    python3 \
    py3-pip \
    wget \
    curl \
    fontconfig \
    ttf-dejavu \
    ttf-liberation \
    font-noto

# Font cache
RUN fc-cache -fv

WORKDIR /app

# Copy requirements first
COPY requirements.txt .

# Install Python packages
RUN pip3 install --no-cache-dir --break-system-packages -r requirements.txt

# Copy app
COPY app.py .

EXPOSE 5000

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "900", "app:app"]
