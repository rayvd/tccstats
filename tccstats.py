#!/usr/bin/python
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
import ConfigParser

from darksky import forecast
from influxdb import InfluxDBClient

# Honeywell TCC SOAP API WSDL URL
HW_URL = 'https://tccna.honeywell.com/ws/MobileV2.asmx?WSDL'

CONFIG = "{}/tccstats.conf".format(os.path.dirname(os.path.realpath(__file__)))

def response_parse(resp, tree):
    """Return text value of a SOAP response body

    Keyword arguments:
    resp -- The response object
    tree -- A list of SOAP response hierarchy elements

    Returns:
    A string"""

    obj = resp.getChild("soap:Envelope").getChild("soap:Body")
    for x in tree:
        obj = obj.getChild(x)
    return obj.getText()

def thermostat_stats(resp):
    """Given a SOAP response containing thermostat information, return a
    dictionary containing temperature details."""

    ret_dict = {}
    attrs = ['GetThermostatResponse', 'GetThermostatResult',
        'Thermostat', 'UI']

    current_temp = response_parse(resp, attrs+['DispTemperature'])
    #outdoor_temp = response_parse(resp, attrs+['OutdoorTemp'])

    ret_dict['current_temp'] = float(current_temp)

    return ret_dict


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
    urllib3.disable_warnings()

    stats = {}

    # Load our configuration file.
    config = ConfigParser.ConfigParser()
    config.read(CONFIG)

    # Get Honeywell related configuration options.
    honeywell = config.items('honeywell')

    # Get Dark Sky API key and lat/long
    ds_apikey = config.get('darksky', 'apikey')
    ds_lat = config.getfloat('darksky', 'lat')
    ds_long = config.getfloat('darksky', 'long')

    # Get our InfluxDB Settings
    if_config = {
        'host': config.get('influxdb', 'host'),
        'port': config.getint('influxdb', 'port'),
        'username': config.get('influxdb', 'username'),
        'password': config.get('influxdb', 'password'),
        'database': config.get('influxdb', 'database')
    }

    t = tcc.tcc(**dict(honeywell))
    stats['current_temp'] = t.get_temp_indoor()

    # Get current temperature from Dark Sky
    ds_stats = forecast(ds_apikey, ds_lat, ds_long)
    stats['outdoor_temp'] = ds_stats.currently.temperature

    # Save statistics to database.
    save_stats(stats, if_config)

if __name__ == '__main__':
    main()
