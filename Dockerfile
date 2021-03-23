FROM python:3.9-slim-buster

LABEL maintainer="Christopher Nethercott" \
    description="PiHole to InfluxDB data bridge"

# Install Python packages
COPY requirements.txt /
RUN pip install -r /requirements.txt

# Clean up
RUN apt-get -q -y autoremove
RUN apt-get -q -y clean
RUN rm -rf /var/lib/apt/lists/*

# Final setup & execution
COPY . /app
WORKDIR /app
CMD ["python3", "-u", "main.py"]