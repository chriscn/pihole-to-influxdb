import time
import datetime
import os
import sys
import logging

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pihole import PiHole # PiHole API Wrapper

logger = logging.Logger('pihole-to-influxdb')
logger.addHandler(logging.StreamHandler(sys.stdout))

try:
    # optional Logger Settings
    logging.basicConfig(level=os.getenv("LOGLEVEL", "DEBUG"))

    # InfluxDB Settings
    DB_URL = os.environ['INFLUX_DB_URL']
    DB_ORG = os.environ['INFLUX_DB_ORG']
    DB_TOKEN = os.environ['INFLUX_DB_TOKEN']
    DB_BUCKET = os.environ['INFLUX_DB_BUCKET']

    # PiHole Settings
    PIHOLE_HOSTNAME = str(os.environ['PIHOLE_HOSTNAME'])
    TEST_INTERVAL = int(os.environ['PIHOLE_INTERVAL'])

    # optional Pi-hole authentication
    AUTHENTICATION_TOKEN = os.getenv('PIHOLE_AUTHENTICATION', None)

except KeyError as e:
    logger.fatal('Missing environment variable: {}'.format(e))
    sys.exit(1)

influxdb_client = InfluxDBClient(DB_URL, DB_TOKEN, org=DB_ORG)

def get_data_for_influxdb(pihole: PiHole, timestamp: datetime.datetime):
    return [
        Point("domains") \
            .time(timestamp) \
            .tag("hostname", PIHOLE_HOSTNAME) \
            .field("domain_count", int(pihole.domain_count.replace(',',''))) \
            .field("unique_domains", int(pihole.unique_domains.replace(',',''))) \
            .field("forwarded", int(pihole.forwarded.replace(',',''))) \
            .field("cached", int(pihole.cached.replace(',',''))),

        Point("queries") \
            .time(timestamp) \
            .tag("hostname", PIHOLE_HOSTNAME) \
            .field("queries", int(pihole.queries.replace(',',''))) \
            .field("blocked", int(pihole.blocked.replace(',',''))) \
            .field("ads_percentage", float(pihole.ads_percentage)),

        Point("clients") \
            .time(timestamp) \
            .tag("hostname", PIHOLE_HOSTNAME) \
            .field("total_clients", int(pihole.total_clients.replace(',',''))) \
            .field("unique_clients", int(pihole.unique_clients.replace(',',''))) \
            .field("total_queries", int(pihole.total_queries.replace(',',''))),

        Point("other") \
            .time(timestamp) \
            .tag("hostname", PIHOLE_HOSTNAME) \
            .field("status", pihole.status == 'enabled') \
            .field("gravity_last_update", pihole.gravity_last_updated['absolute'])
    ]

def get_authenticated_data_for_influxdb(pihole: PiHole, timestamp: datetime.datetime):
    query_type_point = Point("query_types") \
        .time(timestamp) \
        .tag("hostname", PIHOLE_HOSTNAME)
    
    for key, value in pihole.query_types.items():
        query_type_point.field(key, float(value))

    forward_destinations_point = Point("forward_destinations") \
        .time(timestamp) \
        .tag("hostname", PIHOLE_HOSTNAME)
    
    for key, value in pihole.forward_destinations['forward_destinations'].items():
        forward_destinations_point.field(key.split('|')[0], value)

    return [
        query_type_point,
        forward_destinations_point
    ]

class Auth(object):
    def __init__(self, token):
        # PiHole's web token is just a double sha256 hash of the utf8 encoded password
        self.token = token
        self.auth_timestamp = time.time()

def main():
    # pihole ctor has side effects, so we create it locally
    pihole = PiHole(PIHOLE_HOSTNAME)

    write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)

    USE_AUTHENTICATION = False if AUTHENTICATION_TOKEN == None else True

    if USE_AUTHENTICATION:
        try:
            pihole.auth_data = Auth(AUTHENTICATION_TOKEN)
            pihole.refresh()
            logger.info('Pi-Hole authentication successful')
        except Exception as e:
            logger.exception('Pi-Hole authentication failed')
            USE_AUTHENTICATION = False
            raise
    
    next_update = time.monotonic()

    while True:
        try:

            pihole.refresh()
            timestamp = datetime.datetime.now()
            data = get_data_for_influxdb(pihole, timestamp)

            if USE_AUTHENTICATION:
                authenticated_data = get_authenticated_data_for_influxdb(pihole, timestamp)
                try:
                    write_api.write(bucket=DB_BUCKET, record=authenticated_data)
                except Exception as e:
                    logger.exception('Failed to write authenticated data to InfluxDB')

            try:
                write_api.write(bucket=DB_BUCKET, record=data)
                logger.debug('Wrote data to InfluxDB')
                sleep_duration = TEST_INTERVAL
            except Exception as e:
                logger.exception('Failed to write data to InfluxDB')
                # Sleep at most two minutes
                sleep_duration = min(TEST_INTERVAL, 120)

        except Exception as e:
            logger.exception('Failed to get data from Pi-Hole')
            # Sleep at most two minutes
            sleep_duration = min(TEST_INTERVAL, 120)

        next_update = next_update + sleep_duration
        logger.debug("Now sleeping for {}".format(datetime.timedelta(seconds=sleep_duration)))
        time.sleep(max(0, next_update - time.monotonic()))

if __name__ == '__main__':
    logger.info('PiHole Data Logger to InfluxDB')
    main()