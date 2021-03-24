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

# Authentication
AUTHENTICATION_TOKEN = os.environ.get('PIHOLE_AUTHENTICATION')
USE_AUTHENTICATION = False if AUTHENTICATION_TOKEN == None else True

pihole = ph.PiHole(PIHOLE_HOSTNAME)
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
        },
        {
            'measurement': 'other',
            'time': datetime.datetime.now(),
            'fields': {
                'status': True if pihole.status == 'enabled' else False,
                'gravity_last_update': pihole.gravity_last_updated['absolute']
            }
        }
    ]

    return influx_data

def get_formatted_authenticated_forward_destinations():
    formatted_dict = {}
    for key in pihole.forward_destinations['forwarded_destinations']:
        formatted_dict[key.split('|')[0]] = pihole.forward_destinations['forwarded_destinations'][key]
    
    return formatted_dict

def get_authenticated_data_for_influxdb():
    influx_data = [
        {
            'measurement': 'authenticated_query_types',
            'time': datetime.datetime.now(),
            'fields': pihole.query_types
        },
        {
            'measurement': 'authenticated_forward_destinations',
            'time': datetime.datetime.now(),
            'fields': get_formatted_authenticated_forward_destinations()
        }
    ]

    return influx_data

def main():
    init_db()

    if USE_AUTHENTICATION:
        try:
            pihole.authenticate(AUTHENTICATION_TOKEN)
            pihole.refresh()
        except:
            print("{} - Authentication failed using token: {}, disabling authentication.".format(datetime.datetime.now(), AUTHENTICATION_TOKEN))
            USE_AUTHENTICATION = False
            raise

    while(1):
        pihole.refresh()
        data = get_data_for_influxdb()

        if USE_AUTHENTICATION:
            authenticated_data = get_authenticated_data_for_influxdb()
            if influxdb_client.write_points(authenticated_data) == True:
                print("{} - Authenticated data written to DB successfully".format(datetime.datetime.now()))
            else:
                print('{} - Failed to write authenticated points to the database'.format(datetime.datetime.now()))

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