import time
import datetime
import os
import sys
import logging
from enum import Enum

from influxdb_client import InfluxDBClient, Point
from influxdb_client.client.write_api import SYNCHRONOUS
from pihole import PiHole

logger = logging.Logger('pihole-to-influxdb')
logger.addHandler(logging.StreamHandler(sys.stdout))

class AppMode(Enum):
  Live = 1
  Totals = 2
  Raw = 3

try:
  # optional Logger Settings
  logging.basicConfig(level=os.getenv("LOG_LEVEL", "DEBUG"))

  # InfluxDB Settings
  DB_URL = os.environ['INFLUX_DB_URL']
  DB_ORG = os.environ['INFLUX_DB_ORG']
  DB_TOKEN = os.environ['INFLUX_DB_TOKEN']
  DB_BUCKET = os.environ['INFLUX_DB_BUCKET']

  # PiHole Settings
  PIHOLE_URL = str(os.environ['PIHOLE_URL'])
  QUERY_INTERVAL = int(os.environ['PIHOLE_INTERVAL'])

  # optional Pi-hole authentication
  AUTHENTICATION_TOKEN = os.getenv('PIHOLE_AUTHENTICATION', None)

  # optional App Mode
  APP_MODE = AppMode(os.getenv('APP_MODE', 'Totals'))

except KeyError as e:
  logger.fatal('Missing environment variable: {}'.format(e))
  sys.exit(1)
except ValueError as e:
  logger.fatal('Invalid environment variable: {}'.format(e))
  sys.exit(1)

if APP_MODE != AppMode.Totals and not AUTHENTICATION_TOKEN:
  logger.fatal('Pi-hole authentication token is required for live data')
  sys.exit(1)

influxdb_client = InfluxDBClient(DB_URL, DB_TOKEN, org=DB_ORG)
pihole = PiHole(PIHOLE_URL, AUTHENTICATION_TOKEN)

def main():
  write_api = influxdb_client.write_api(write_options=SYNCHRONOUS)
  next_update = time.monotonic()

  logger.info('Starting PiHole Data Logger to InfluxDB')
  logger.info('AppMode: {}'.format(APP_MODE))

  # Test Pi-hole connection
  try:
    pihole.request_summary()
  except Exception as e:
    logger.fatal('Unable to connect to Pi-hole: {}'.format(e))
    sys.exit(1)

  while True:
    try:
      if APP_MODE == AppMode.Live:
        timestamp = datetime.datetime.now()
        data = list(pihole.get_queries_for_influxdb(timestamp, QUERY_INTERVAL))
      elif APP_MODE == AppMode.Totals:
        data = list(pihole.get_totals_for_influxdb())
      elif APP_MODE == AppMode.Raw:
        data = list(pihole.get_query_logs_for_influxdb())

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
  main()