#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import requests
from datetime import datetime
from enum import Enum
from influxdb_client import Point

class PiHole:
  def __init__(self, host, password):
    self.host = host
    if host.startswith("http"):
      self.url = host
    else:
      self.url = f"http://{host}"

    if password:
      json = self.post("auth", {'password': password}).json()
      if not 'session' in json or not json['session']['valid']:
        print(f"auth response: {json}")
      self.sid = json['session']['sid']
      self.csrf = json['session'].get('csrf', None)

  def post(self, endpoint, params={}):
    return requests.post(f"{self.url}/api/{endpoint}", json=params)

  def query(self, endpoint, params={}):
    return requests.get(f"{self.url}/api/{endpoint}", params=params)
  
  def request_all_queries(self, start: float, end: float):
    if not self.sid:
      raise Exception("Password required")
    params = {
      "from": int(start),
      "until": int(end),
      "length": 100000,
      "sid": self.sid
      }
    json = self.query("queries", params=params).json()
    if not 'queries' in json:
      print(f"API response: {json}")
    return json['queries']

  def request_summary(self):
    if not self.sid:
      raise Exception("Password required")
    params = {
      "sid": self.sid
    }
    json = self.query("stats/summary", params=params).json()
    return json
  
  def request_forward_destinations(self):
    if not self.sid:
      raise Exception("Password required")
    params = {
      "sid": self.sid
      }
    json = self.query("stats/upstreams", params=params).json()
    if not 'upstreams' in json:
      print(f"API response: {json}")
    return json['upstreams']

  def get_totals_for_influxdb(self):
    summary = self.request_summary()
    timestamp = datetime.now().astimezone()
    yield Point("domains") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("domain_count", summary['gravity']['domains_being_blocked']) \
      .field("unique_domains", summary['queries']['unique_domains']) \
      .field("forwarded", summary['queries']['forwarded']) \
      .field("cached", summary['queries']['cached'])
      
    yield Point("queries") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("queries", summary['queries']['total']) \
      .field("blocked", summary['queries']['blocked']) \
      .field("ads_percentage", summary['queries']['percent_blocked'])
      
    yield Point("clients") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("total_clients", summary['clients']['total']) \
      .field("unique_clients", summary['clients']['active']) \
      .field("total_queries", sum(summary['queries']['types'].values()))
      
    yield Point("other") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("gravity_last_update", summary['gravity']['last_update'])

    for key, value in summary['queries']['types'].items():
      yield Point("query_types") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("query_type", key) \
        .field("value", float(value))

    forward_destinations = self.request_forward_destinations()
    for upstream in forward_destinations:
      yield Point("forward_destinations") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("ip", upstream['ip']) \
        .tag("destination", upstream['name'] or upstream['ip']) \
        .field("value", float(upstream['count']))
  
  def get_queries_for_influxdb(self, query_date: datetime, sample_period: int):
    # Get all queries since last sample
    end_time = query_date.timestamp()
    start_time = end_time - sample_period + 1
    queries = self.request_all_queries(start_time, end_time)
    timestamp = datetime.now().astimezone()

    # we still need some stats from the summary
    summary = self.request_summary()

    yield Point("domains") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("domain_count", summary['gravity']['domains_being_blocked']) \
      .field("unique_domains", len(set(x['domain'] for x in queries))) \
      .field("forwarded", sum(1 for x in queries if x['status'].startswith("FORWARDED"))) \
      .field("cached", sum(1 for x in queries if x['status'].startswith("CACHED")))
    
    blocked_count = sum(1 for x in queries if x['status'].startswith("BLOCKED") or x['status'].startswith("BLACKLIST"))
    queries_point = Point("queries") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("queries", len(queries)) \
      .field("blocked", blocked_count) \
      .field("ads_percentage", blocked_count * 100.0 / max(1, len(queries)))
    yield queries_point

    clients = {}
    for query in queries:
      name = query['client']['name'] or query['client']['ip']
      group = clients.get(name, [])
      group.append(query)
      clients[name] = group
    for name, group in clients.items():
      blocked_count = sum(1 for x in group if x['status'].startswith("BLOCKED") or x['status'].startswith("BLACKLIST"))
      clients_point = Point("clients") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("client", name) \
        .field("queries", len(group)) \
        .field("blocked", blocked_count) \
        .field("ads_percentage", blocked_count * 100.0 / max(1, len(group)))
      yield clients_point

    yield Point("other") \
      .time(timestamp) \
      .tag("hostname", self.host) \
      .field("gravity_last_update", summary['gravity']['last_update'])

    for key in summary['queries']['types']:
      yield Point("query_types") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("query_type", key) \
        .field("queries", sum(1 for x in queries if x['type'] == key))

    destinations = {}
    for query in queries:
      if query['upstream']:
        name = query['upstream'].split('#')[0]
        group = clients.get(name, [])
        group.append(query)
        clients[name] = group
    for name, group in destinations.items():
      yield Point("forward_destinations") \
        .time(timestamp) \
        .tag("hostname", self.host) \
        .tag("destination", name) \
        .field("queries", len(group))

  def get_query_logs_for_influxdb(self, query_date: datetime, sample_period: int):
    end_time = query_date.timestamp()
    start_time = end_time - sample_period + 1

    for query in self.request_all_queries(start_time, end_time):
      p = Point("logs") \
        .time(datetime.fromtimestamp(query['time'])) \
        .tag("hostname", self.host) \
        .tag("query_type", query['type']) \
        .field("domain", query['domain']) \
        .tag("client", query['client']['name'] or query['client']['ip']) \
        .tag("status", query['status'][0] + query['status'][1:].lower()) \
        .tag("reply_type", query['reply']['type']) \
        .field("reply_time", query['reply']['time']) \
        .tag("dnssec", query['dnssec'][0] + query['dnssec'][1:].lower())
      if query['upstream']:
        p.tag("destination", query['upstream'].split('#')[0])
      yield p

if __name__ == "__main__":
  import argparse
  parser = argparse.ArgumentParser(description='Export Pi-Hole statistics')
  parser.add_argument('--host', required=True, type=str, help='Pi-Hole host')
  parser.add_argument('--password', '-t', required=True, type=str, help='Pi-Hole API password')
  args = parser.parse_args()
  pihole = PiHole(host=args.host, password=args.password)

  points = list(pihole.get_queries_for_influxdb(datetime.now(), 600))
  for p in points:
    print(p._time, p._name, p._tags, p._fields)