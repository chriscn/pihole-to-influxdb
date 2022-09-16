#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from datetime import datetime
from enum import Enum
from influxdb_client import Point
from pandas import DataFrame
from urllib.parse import urlparse

class QueryStati(Enum):
  Blocked = 1
  Forwarded = 2
  Cached = 3
  Wildcard = 4
  Unknown = 5

class PiHole:
  def __init__(self, url, token):
    self.host = url
    self.url = urlparse(url)
    self.token = token

  def query(self, endpoint, params={}):
    url = "{}://{}/admin/{}.php".format(self.url.scheme or "http", self.url.netloc, endpoint)
    return requests.get(url, params=params)
  
  def request_all_queries(self, start: float, end: float):
    """
    keys[]: time, query_type, domain, client, status, destination, reply_type, reply_time, dnssec
    """
    if not self.token:
      raise Exception("Token required")
    params = {
      "getAllQueries": "",
      "from": int(start),
      "until": int(end),
      "auth": self.token
      }
    json = self.query("api_db", params=params).json()
    if json:
      return json['data']
    else:
      return []

  def request_summary(self):
    """
    keys: 
      - domains_being_blocked
      - dns_queries_today
      - ads_blocked_today
      - ads_percentage_today
      - unique_domains
      - queries_forwarded
      - queries_cached
      - clients_ever_seen
      - unique_clients
      - dns_queries_all_types
      - reply_UNKNOWN
      - reply_NODATA
      - reply_NXDOMAIN
      - reply_CNAME
      - reply_IP
      - reply_DOMAIN
      - reply_RRNAME
      - reply_SERVFAIL
      - reply_REFUSED
      - reply_NOTIMP
      - reply_OTHER
      - reply_DNSSEC
      - reply_NONE
      - reply_BLOB
      - dns_queries_all_replies
      - privacy_level
      - status
      - gravity_last_update: file_exists, absolute, relative
    """
    json = self.query("api").json()
    return json
  
  def request_forward_destinations(self):
    if not self.token:
      raise Exception("Token required")
    params = {
      "getForwardDestinations": "",
      "auth": self.token
      }
    json = self.query("api", params=params).json()
    if json:
      return json['forward_destinations']
    else:
      return {}

  def request_query_types(self):
    if not self.token:
      raise Exception("Token required")
    params = {
      "getQueryTypes": "",
      "auth": self.token
      }
    json = self.query("api", params=params).json()
    if json:
      return json['querytypes']
    else:
      return {}

  def get_totals_for_influxdb(self):
    summary = self.request_summary()
    timestamp = datetime.now().astimezone()
    yield Point("domains") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("domain_count", summary['domains_being_blocked']) \
      .field("unique_domains", summary['unique_domains']) \
      .field("forwarded", summary['queries_forwarded']) \
      .field("cached", summary['queries_cached'])
      
    yield Point("queries") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("queries", summary['dns_queries_today']) \
      .field("blocked", summary['ads_blocked_today']) \
      .field("ads_percentage", summary['ads_percentage_today'])
      
    yield Point("clients") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("total_clients", summary['clients_ever_seen']) \
      .field("unique_clients", summary['unique_clients']) \
      .field("total_queries", summary['dns_queries_all_types'])
      
    yield Point("other") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("status", summary['status'] == 'enabled') \
      .field("gravity_last_update", summary['gravity_last_updated']['absolute'])

    if self.token:
      query_types = self.request_query_types()
      for key, value in query_types.items():
        yield Point("query_types") \
          .time(timestamp) \
          .tag("hostname", self.host) \
          .tag("query_type", key) \
          .field("value", float(value))

      forward_destinations = self.request_forward_destinations()
      for key, value in forward_destinations.items():
        yield Point("forward_destinations") \
          .time(timestamp) \
          .tag("hostname", self.host) \
          .tag("destination", key.split('|')[0]) \
          .field("value", float(value))
  
  def get_queries_for_influxdb(self, query_date: datetime, sample_period: int):
    # Get all queries since last sample
    end_time = query_date.timestamp()
    start_time = end_time - sample_period + 1
    queries = self.request_all_queries(start_time, end_time)
    timestamp = datetime.now().astimezone()
    df = DataFrame(queries, columns=['time', 'query_type', 'domain', 'client', 'status', 'destination', 'reply_type', 'reply_time', 'dnssec'])

    # we still need some stats from the summary
    summary = self.request_summary()

    yield Point("domains") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("domain_count", summary['domains_being_blocked']) \
      .field("unique_domains", len(df.groupby('domain'))) \
      .field("forwarded", len(df[df['status'] == QueryStati.Forwarded.value])) \
      .field("cached", len(df[df['status'] == QueryStati.Cached.value]))
    
    blocked_count = len(df[(df['status'] == QueryStati.Blocked.value) | (df['status'] == QueryStati.Wildcard.value)])
    queries_point = Point("queries") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("queries", len(df)) \
      .field("blocked", blocked_count) \
      .field("ads_percentage", blocked_count * 100.0 / max(1, len(df)))
    yield queries_point

    for key, client_df in df.groupby('client'):
      blocked_count = len(client_df[(client_df['status'] == QueryStati.Blocked.value) | (client_df['status'] == QueryStati.Wildcard.value)])
      clients_point = Point("clients") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("client", key) \
        .field("queries", len(client_df)) \
        .field("blocked", blocked_count) \
        .field("ads_percentage", blocked_count * 100.0 / max(1, len(client_df)))
      yield clients_point

    yield Point("other") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("status", summary['status'] == 'enabled') \
      .field("gravity_last_update", summary['gravity_last_updated']['absolute'])

    for key, group_df in df.groupby('query_type'):
      yield Point("query_types") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("query_type", key) \
        .field("queries", len(group_df))

    for key, group_df in df.groupby('destination'):
      yield Point("forward_destinations") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("destination", key.split('|')[0]) \
        .field("queries", len(group_df))

  def get_query_logs_for_influxdb(self, query_date: datetime, sample_period: int):
    end_time = query_date.timestamp()
    start_time = end_time - sample_period + 1

    for data in self.request_all_queries(start_time, end_time):
      timestamp, query_type, domain, client, status, destination, reply_type, reply_time, dnssec = data
      p = Point("logs") \
        .time(datetime.fromtimestamp(timestamp)) \
        .tag("hostname", self.host) \
        .tag("query_type", query_type) \
        .field("domain", domain) \
        .tag("client", client) \
        .tag("status", QueryStati(status)) \
        .tag("dnssec", dnssec != 0) \
        .field("reply_time", reply_time)
      if destination:
        p.tag("destination", destination)
      yield p

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Export Pi-Hole statistics')
  parser.add_argument('--host', required=True, type=str, help='Pi-Hole host')
  parser.add_argument('--token', '-t', required=True, type=str, help='Pi-Hole API token')
  args = parser.parse_args()
  pihole = PiHole(host=args.host, token=args.token)

  points = list(pihole.get_queries_for_influxdb(datetime.now(), 600))
  for p in points:
    print(p._time, p._name, p._tags, p._fields)