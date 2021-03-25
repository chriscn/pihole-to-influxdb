# pihole-to-influxdb
## Introduction
Based slightly on my other project, [speedtest-to-influxdb](https://github.com/chriscn/speedtest-to-influxdb). This project leverages the [Pi-Hole](https://pi-hole.net/) API to gather data about your PiHole instance and store it inside of InfluxDB for your future projects.

This project is automatically built through GitHub actions and the DockerHub file can be found [here](https://hub.docker.com/r/chriscn/pihole-to-influxdb).
## Setup
### Configuring the script
The InfluxDB connection settings can be configured as followed:
- INFLUX_DB_ADDRESS=192.168.xxx.xxx
- INFLUX_DB_PORT=8086
- INFLUX_DB_USER=user
- INFLUX_DB_PASSWORD=pass
- INFLUX_DB_DATABASE=pihole
The PiHole settings can be configured as followed:
- PIHOLE_HOSTNAME=192.168.xxx.xxx
- PIHOLE_INTERVAL=15 *Interval in seconds*
### Authentication
Certain parts of the API require you to be authenticated, this can be achieved by supplying the `PIHOLE_AUTHENTICATION` token with the password you use to login to the web interface.  
By doing this you'll gain access to two new measurements (tables): 
- authenticated_query_types
- authenticated_forward_destinations
#### Sidenote
This does mean that your password is stored in plaintext as an envronmental variable and as such as malicious actor could find it and access your PiHole instance. You are advised to use this at your own risk.
### Docker Command
```
    docker run -d --name pihole-to-influx \
    -e 'INFLUX_DB_ADDRESS'='_influxdb_host_' \
    -e 'INFLUX_DB_PORT'='8086' \
    -e 'INFLUX_DB_USER'='_influx_user_' \
    -e 'INFLUX_DB_PASSWORD'='_influx_pass_' \
    -e 'INFLUX_DB_DATABASE'='pihole' \
    -e 'PIHOLE_INTERVAL'='1800' \
    -e 'PIHOLE_HOSTNAME'='192.168.xxx.xxx'  \
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
        - INFLUX_DB_ADDRESS=192.168.xxx.xxx
        - INFLUX_DB_PORT=8086
        - INFLUX_DB_USER=user
        - INFLUX_DB_PASSWORD=pass
        - INFLUX_DB_DATABASE=pihole
        - PIHOLE_HOSTNAME=192.168.xxx.xxx
        - PIHOLE_INTERVAL=15
```