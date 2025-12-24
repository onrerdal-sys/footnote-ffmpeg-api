FROM jrottenberg/ffmpeg:4.4-ubuntu

USER root

# Install ONLY Python and pip (fonts already exist in base image)
RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements.txt .

# Install Python packages
RUN pip3 install --no-cache-dir -r requirements.txt

# Copy app
COPY app.py .

EXPOSE 5000

# Override ENTRYPOINT
ENTRYPOINT []

# Start gunicorn
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "2", "--timeout", "900", "app:app"]
