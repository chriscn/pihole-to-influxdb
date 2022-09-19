FROM python:3.9-slim-bullseye

LABEL maintainer="Christopher Nethercott" \
    description="PiHole to InfluxDB data bridge"

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN apt-get update && \
  apt-get install -y --no-install-recommends python3-pandas && \
  pip install -r requirements.txt

# Clean up
RUN apt-get -q -y autoremove && \
  apt-get -q -y clean && \
  rm -rf /var/lib/apt/lists/*

# Final setup & execution
COPY . /app
CMD ["python3", "-u", "main.py"]