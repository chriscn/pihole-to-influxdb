import time
import datetime
import os

from influxdb import InfluxDBClient
import pihole as ph # PiHole API Wrapper

# InfluxDB Settings
DB_ADDRESS = os.environ.get('INFLUX_DB_ADDRESS')
DB_PORT = int(os.environ.get('INFLUX_DB_PORT'))
DB_USER = os.environ.get('INFLUX_DB_USER')
DB_PASSWORD = os.environ.get('INFLUX_DB_PASSWORD')
DB_DATABASE = os.environ.get('INFLUX_DB_DATABASE')

# PiHole Settings
PIHOLE_HOSTNAME = os.environ.get('PIHOLE_HOSTNAME')
TEST_INTERVAL = int(os.environ.get('PIHOLE_INTERVAL'))

pihole = ph.PiHole('192.168.113.250')
influxdb_client = InfluxDBClient(DB_ADDRESS, DB_PORT, DB_USER, DB_PASSWORD, None)

def init_db():
    databases = influxdb_client.get_list_database()

    if len(list(filter(lambda x: x['name'] == DB_DATABASE, databases))) == 0:
        influxdb_client.create_database(DB_DATABASE)  # Create if does not exist.
        print('{} - Created database {}'.format(datetime.datetime.now(), DB_DATABASE))
    else:
        # Switch to if does exist.
        influxdb_client.switch_database(DB_DATABASE)
        print('{} - Switched to database {}'.format(datetime.datetime.now(), DB_DATABASE))

def get_data_for_influxdb():
    influx_data = [
        {
            'measurement': 'domains',
            'time': datetime.datetime.now(),
            'fields': {
                'domain_count': int(pihole.domain_count.replace(',','')),
                'unique_domains': int(pihole.unique_domains.replace(',','')),
                'forwarded': int(pihole.forwarded.replace(',','')),
                'cached': int(pihole.cached.replace(',',''))
            }
        },
        {
            'measurement': 'queries',
            'time': datetime.datetime.now(),
            'fields': {
                'queries': int(pihole.queries.replace(',','')),
                'blocked': int(pihole.blocked.replace(',','')),
                'ads_percentage': float(pihole.ads_percentage)
            }   
        },
        {
            'measurement': 'clients',
            'time': datetime.datetime.now(),
            'fields': {
                'total_clients': int(pihole.total_clients.replace(',','')),
                'unique_clients': int(pihole.unique_clients.replace(',','')),
                'total_queries': int(pihole.total_queries.replace(',',''))
            }
        }
    ]

    return influx_data


def main():
    init_db()

    while(1):
        data = get_data_for_influxdb()
        if influxdb_client.write_points(data) == True:
            print("{} - Data written to DB successfully".format(datetime.datetime.now()))
            print("{} - Now sleeping for {}s".format(datetime.datetime.now(), TEST_INTERVAL))
            time.sleep(TEST_INTERVAL)
        else:
            print('{} - Failed to write points to the database'.format(datetime.datetime.now()))
            time.sleep(120) # Sleep for two seconds.


if __name__ == '__main__':
    print('{} - PiHole Data Logger to InfluxDB'.format(datetime.datetime.now()))
    main()