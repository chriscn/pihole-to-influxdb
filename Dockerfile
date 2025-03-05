FROM python:3.13-alpine

LABEL maintainer="Christopher Nethercott" \
    description="PiHole to InfluxDB data bridge"

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN pip install -r requirements.txt --break-system-packages

# Final setup & execution
COPY . /app
CMD ["python3", "-u", "main.py"]