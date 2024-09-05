FROM debian:12.7-slim

LABEL maintainer="Christopher Nethercott" \
    description="PiHole to InfluxDB data bridge"

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN apt-get update && \
  apt-get install -y --no-install-recommends python3 python3-pip python3-pandas && \
  python3 -m pip install -r requirements.txt --break-system-packages

# Clean up
RUN apt-get -q -y autoremove && \
  apt-get -q -y clean && \
  rm -rf /var/lib/apt/lists/*

# Final setup & execution
COPY . /app
CMD ["python3", "-u", "main.py"]