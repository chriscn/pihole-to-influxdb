import time
import datetime
import os
import sys
import logging

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pihole import PiHole

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
  QUERY_LIVE = bool(os.getenv('PIHOLE_QUERY_LIVE', True))
  QUERY_INTERVAL = int(os.environ['PIHOLE_INTERVAL'])

  # optional Pi-hole authentication
  AUTHENTICATION_TOKEN = os.getenv('PIHOLE_AUTHENTICATION', None)

except KeyError as e:
  logger.fatal('Missing environment variable: {}'.format(e))
  sys.exit(1)

influxdb_client = InfluxDBClient(DB_URL, DB_TOKEN, org=DB_ORG)
pihole = PiHole(PIHOLE_HOSTNAME, AUTHENTICATION_TOKEN)

class Auth(object):
  def __init__(self, token):
    # PiHole's web token is just a double sha256 hash of the utf8 encoded password
    self.token = token
    self.auth_timestamp = time.time()

def main():
  write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
  next_update = time.monotonic()

  while True:
    try:
      timestamp = datetime.datetime.now()
      if QUERY_LIVE:
        data = list(pihole.get_queries_for_influxdb(timestamp, QUERY_INTERVAL))
      else:
        data = list(pihole.get_totals_for_influxdb())

      logger.debug('Writing {} points to InfluxDB'.format(len(data)))
      write_api.write(bucket=DB_BUCKET, record=data)
      sleep_duration = QUERY_INTERVAL

    except Exception as e:
      logger.exception('Failed to get data from Pi-Hole to InfluxDB')
      # Sleep at most two minutes
      sleep_duration = min(QUERY_INTERVAL, 120)

    next_update = next_update + sleep_duration
    logger.debug("Now sleeping for {}".format(datetime.timedelta(seconds=sleep_duration)))
    time.sleep(max(0, next_update - time.monotonic()))

if __name__ == '__main__':
  logger.info('PiHole Data Logger to InfluxDB')
  main()