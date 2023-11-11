FROM alpine:3.18.4

LABEL maintainer="Christopher Nethercott" \
    description="PiHole to InfluxDB data bridge"

WORKDIR /app

# Install Python packages
COPY requirements.txt .
RUN apk add --update --no-cache python3 py3-pip py3-pandas && \
    python3 -m pip install -r requirements.txt

# Cleanup
RUN rm -rf /var/cache/apk/*

# Final setup & execution
COPY . /app
CMD ["python3", "-u", "main.py"]