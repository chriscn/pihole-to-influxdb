# pihole-to-influxdb

## Introduction
Based slightly on my other project, [speedtest-to-influxdb](https://github.com/chriscn/speedtest-to-influxdb). This project leverages the [Pi-Hole](https://pi-hole.net/) API to gather data about your PiHole instance and store it inside of InfluxDB for your future projects. An example dashoard can be found [here](Pi-hole-grafana-dashboard.json).

This project is automatically built through GitHub actions and published to [DockerHub](https://hub.docker.com/r/chriscn/pihole-to-influxdb).

## Setup

### Configuring the script
The InfluxDB connection settings can be configured as followed:
- `INFLUX_DB_URL=http://192.168.xxx.xxx:8086`
- `INFLUX_DB_ORG=<your org name>`
- `INFLUX_DB_TOKEN=<token>`
- `INFLUX_DB_BUCKET=pihole`

The PiHole settings can be configured as followed:
- `PIHOLE_URL=http://192.168.xxx.xxx`
- `PIHOLE_INTERVAL=15` *Interval in seconds*
- `PIHOLE_AUTHENTICATION=<password>`

Optionally you can also configure the following:
- `LOG_LEVEL=DEBUG`
- `APP_MODE=Totals`

### Authentication
The Pi-Hole API requires you to be authenticated. This can be achieved by supplying the `PIHOLE_AUTHENTICATION` environment variable with your password or an API password from the settings page of the admin interface.

#### Sidenote
This does mean that your password is stored in plaintext as an environment variable and as such as malicious actor could find it and access your PiHole instance. You are advised to use this at your own risk.

### App Modes
The `APP_MODE` changes the way the script works. 

There are three modes available to choose from:
- `APP_MODE=Totals` *This is the default mode*
- `APP_MODE=Live`
- `APP_MODE=Raw`

The default mode is `Totals` which will only send the daily totals of the PiHole instance, as displayed in the GUI. Another mode is `Live` which will send a summary of the Pi-hole queries of the last `PIHOLE_INTERVAL` seconds. The last mode is `Raw` which will send the raw data of the Pi-hole queries.

### Docker Command
```
docker run -d --name pihole-to-influx \
  -e 'INFLUX_DB_URL'='<influxdb url>' \
  -e 'INFLUX_DB_ORG'='<influxdb org>' \
  -e 'INFLUX_DB_TOKEN'='<influxdb token>' \
  -e 'INFLUX_DB_BUCKET'='pihole' \
  -e 'PIHOLE_INTERVAL'='1800' \
  -e 'PIHOLE_URL'='192.168.xxx.xxx'  \
  -e 'PIHOLE_AUTHENTICATION'='<password>'  \
  chriscn/pihole-to-influxdb
```

### docker-compose
```yaml
version: '3'
services:
  pihole-to-influxdb:
    image: chriscn/pihole-to-influxdb
    container_name: pihole-to-influxdb
    environment:
    - "INFLUX_DB_URL=http://192.168.xxx.xxx:8086"
    - "INFLUX_DB_ORG=myOrg"
    - "INFLUX_DB_TOKEN=<token>"
    - "INFLUX_DB_BUCKET=pihole"
    - "PIHOLE_URL=http://192.168.xxx.xxx"
    - "PIHOLE_INTERVAL=15"
    - "PIHOLE_AUTHENTICATION=<password>"
    - "LOG_LEVEL=DEBUG"
    - "APP_MODE=Totals"
```