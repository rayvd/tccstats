#!/usr/bin/env python2
#
# Retrieve temperature stats from our Honeywell Wifi 9000 thermometer, outdoor
# temperature from Dark Sky and then store in our InfluxDB database for
# display in Grafana.
#

import os
import sys
import tcc
import urllib3
import argparse
import requests
import ConfigParser

from influxdb import InfluxDBClient

CONFIG = "{}/tccstats.conf".format(os.path.dirname(os.path.realpath(__file__)))
PW_API_URL = "https://api.pirateweather.net/forecast/"

def save_stats(stats, if_config):
    """Save a dictionary of statistics to an InfluxDB database.

    Keyword arguments:
    stats -- A dictionary containing our statistics.
    if_config -- Configuration elements for talking to InfluxDB

    Returns:
    None"""

    # Instantiate our client connection.
    client = InfluxDBClient(host=if_config['host'], port=if_config['port'],
        username=if_config['username'], password=if_config['password'], 
        database=if_config['database'], ssl=True, verify_ssl=False) 

    # Set up our JSON payload.
    body = [
        {
            "measurement": "temperature",
            "tags": {
                "thermostat": "Honeywell Wifi 9000"
            },
            "fields": {
                "indoor": stats['current_temp'],
                "outdoor": stats['outdoor_temp']
            }
        }
    ]

    # Write!
    client.write_points(body)

    # Logout.
    client.close()

def main():
    # Our InfluxDB uses HTTPS, but is using a self-signed certificate.
    # https://stackoverflow.com/questions/27981545/suppress-insecurerequestwarning-unverified-https-request-is-being-made-in-pytho
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    # We accept --init as a parameter
    parser = argparse.ArgumentParser()
    parser.add_argument('--init', dest='token_init', action='store_true')
    args = parser.parse_args()

    # Initialize a dict to store our statistics.
    stats = {}

    # Load our configuration file.
    config = ConfigParser.ConfigParser()
    config.read(CONFIG)

    # Get Honeywell related configuration options.
    honeywell = config.items('honeywell')

    # Get Dark Sky API key and lat/long
    pw_apikey = config.get('pirateweather', 'apikey')
    pw_lat = config.getfloat('pirateweather', 'lat')
    pw_long = config.getfloat('pirateweather', 'long')

    # Get our InfluxDB Settings
    if_config = {
        'host': config.get('influxdb', 'host'),
        'port': config.getint('influxdb', 'port'),
        'username': config.get('influxdb', 'username'),
        'password': config.get('influxdb', 'password'),
        'database': config.get('influxdb', 'database')
    }

    # Pull the indoor temperature from the thermostat.
    if args.token_init:
        t = tcc.tcc(token_init=True, **dict(honeywell))
    else:
        t = tcc.tcc(**dict(honeywell))

    # Read current indoor temperature
    stats['current_temp'] = t.get_temp_indoor()

    # Get current temperature from Pirate Weather 
    pw_url = "{}{}/{},{}".format(PW_API_URL, pw_apikey, pw_lat, pw_long)
    stats['outdoor_temp'] = requests.get(pw_url).json()['currently']['temperature']

    # Save statistics to database.
    save_stats(stats, if_config)

if __name__ == '__main__':
    main()
