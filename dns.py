#!/usr/bin/env python
"""
LICENSE http://www.apache.org/licenses/LICENSE-2.0
"""

import argparse
import datetime
import sys
import time
import threading
import traceback
import socketserver
import struct
import json
from math import sin, cos, sqrt, atan2, pow  # for the haversine_distance function
import requests
try:
    from dnslib import *
except ImportError:
    print("Missing dependency dnslib: <https://pypi.python.org/pypi/dnslib>. Please install it with `pip`.")
    sys.exit(2)

import requests

import logging

def setup_logging():
    logging.basicConfig(filename='log.txt', level=logging.INFO, format='%(asctime)s - %(levelname)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')

def log_to_file(*args):
    # Use the first argument as the log message format and the rest as values
    message_format = args[0]
    values = args[1:]

    # Check if any of the values is a list and concatenate its elements
    values = [", ".join(map(str, val)) if isinstance(val, list) else val for val in values]

    # Combine the format and values into a log message
    log_message = message_format.format(*values)

    # Log the message
    logging.info(log_message)

setup_logging()

def read_config():
    with open("config.json", "r") as config_file:
        config_data = json.load(config_file)
        dns_ip = config_data["dns_ip"]
        api_key = config_data["api_key"]
        algorithms = config_data["algorithm"]
        algorithm = random.choice(algorithms)
    return dns_ip, api_key, algorithm, config_data

DNS_IP, API_KEY, ALGORITHM, config = read_config()

def get_coordinates(ip_address, api_key):
    # Make a request to the IP Stack API to get the location information
    url = f"http://api.ipstack.com/{ip_address}?access_key={api_key}"
    response = requests.get(url)
    data = response.json()

    # Extract latitude and longitude from the API response
    latitude = data["latitude"]
    longitude = data["longitude"]
    log_to_file('Latitude : {}',latitude)
    log_to_file('Longitude: {}',longitude)
    return latitude, longitude

def haversine_distance(coord1, coord2):
    # Haversine formula to calculate distance between two points on the Earth's surface
    lat1, lon1 = coord1
    lat2, lon2 = coord2

    R = 6371  # Radius of the Earth in kilometers

    dlat = (lat2 - lat1) * (3.14159 / 180.0)
    dlon = (lon2 - lon1) * (3.14159 / 180.0)

    a = (pow(sin(dlat / 2), 2) + cos(lat1 * (3.14159 / 180.0)) * cos(lat2 * (3.14159 / 180.0)) * pow(sin(dlon / 2), 2))
    c = 2 * atan2(sqrt(a), sqrt(1 - a))

    distance = R * c  # Distance in kilometers

    return distance

def ip_distance(ip1, ip2, api_key):
    # Get coordinates for both IP addresses
    coord1 = get_coordinates(ip1, api_key)
    coord2 = get_coordinates(ip2, api_key)

    # Calculate distance using Haversine formula
    distance = haversine_distance(coord1, coord2)

    return distance

def get_min_distance_ip(api_key):
    global ip_list
    min_distance = float('inf')
    min_distance_ip = None

    for ip in ip_list:
        distance = ip_distance(ip, DNS_IP, api_key)
        if distance < min_distance:
            min_distance = distance
            min_distance_ip = ip

    log_to_file('Minimum Distance Ip : {}',min_distance_ip)
    return min_distance_ip

# Add the following function to read the load values from the file
def read_load_values():
    with open("load.txt", "r") as load_file:
        load_values = [float(line.strip()) for line in load_file.readlines() if line != ""]
    return load_values

def get_min_load_ip():
    global ip_list
    load_values = read_load_values()

    min_load = float('inf')
    min_load_ip = None

    for ip, load in zip(ip_list, load_values):
        if load < min_load:
            min_load = load
            min_load_ip = ip
    log_to_file('Minimum Load Ip : {}',min_load_ip)
    return min_load_ip


class DomainName(str):
    def __getattr__(self, item):
        return DomainName(item + '.' + self)


D = DomainName('dnsserver-saidivyasreesheema.online.')
IP = None
TTL = 60 * 5

soa_record = SOA(
    mname=D.ns1,  # primary name server
    rname=D.andrei,  # email of the domain administrator
    times=(
        201307231,  # serial number
        60 * 60 * 1,  # refresh
        60 * 60 * 3,  # retry
        60 * 60 * 24,  # expire
        60 * 60 * 1,  # minimum
    )
)
ns_records = [NS(D.ns1), NS(D.ns2)]
records = None
log_to_file('Domain Name : dnsserver-saidivyasreesheem.online')
ip_list = [i.strip() for i in open("ip.cfg", "r").readlines() if i != ""]
print(ip_list)
lock = threading.Lock()

def get_ip():
    global IP
    global records
    lock.acquire()
    if ALGORITHM == "round":
        ip = ip_list.pop(0)
        IP = ip
        ip_list.append(ip)
        log_to_file('Algorithm Used  : ROUND ROBIN')
    elif ALGORITHM == "geo":
        IP = get_min_distance_ip(API_KEY)
        log_to_file('Algorithm Used  : GEO APPROXIMATION')
    elif ALGORITHM == "load":
        IP = get_min_load_ip()
        log_to_file('Algorithm Used  : LOAD-BASED')
    lock.release()

    records = {
        D: [A(IP), AAAA((0,) * 16), MX(D.mail), soa_record] + ns_records,
        D.ns1: [A(IP)],  # MX and NS records must never point to a CNAME alias (RFC 2181 section 10.3)
        D.ns2: [A(IP)],
        D.mail: [A(IP)],
        D.andrei: [CNAME(D)],
    }
    print(ip_list)
    
    log_to_file("Ip List Used :{} ",ip_list)
get_ip()

def dns_response(data):
    request = DNSRecord.parse(data)

    print(request)
    log_to_file("DNS Request : {}",request)

    reply = DNSRecord(DNSHeader(id=request.header.id, qr=1, aa=1, ra=1), q=request.q)

    qname = request.q.qname
    qn = str(qname)
    qtype = request.q.qtype
    qt = QTYPE[qtype]

    if qn == D or qn.endswith('.' + D):

        for name, rrs in records.items():
            if name == qn:
                for rdata in rrs:
                    rqt = rdata.__class__.__name__
                    if qt in ['*', rqt]:
                        reply.add_answer(RR(rname=qname, rtype=getattr(QTYPE, rqt), rclass=1, ttl=TTL, rdata=rdata))

        for rdata in ns_records:
            reply.add_ar(RR(rname=D, rtype=QTYPE.NS, rclass=1, ttl=TTL, rdata=rdata))

        reply.add_auth(RR(rname=D, rtype=QTYPE.SOA, rclass=1, ttl=TTL, rdata=soa_record))

    print("---- Reply:\n", reply)

    return reply.pack()


class BaseRequestHandler(socketserver.BaseRequestHandler):

    def get_data(self):
        raise NotImplementedError

    def send_data(self, data):
        raise NotImplementedError

    def handle(self):
        now = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        print("\n\n%s request %s (%s %s):" % (self.__class__.__name__[:3], now, self.client_address[0],
                                               self.client_address[1]))
        try:
            data = self.get_data()
            print(len(data), data)  # repr(data).replace('\\x', '')[1:-1]
            self.send_data(dns_response(data))
        except Exception:
            traceback.print_exc(file=sys.stderr)


class TCPRequestHandler(BaseRequestHandler):

    def get_data(self):
        data = self.request.recv(8192).strip()
        sz = struct.unpack('>H', data[:2])[0]
        if sz < len(data) - 2:
            raise Exception("Wrong size of TCP packet")
        elif sz > len(data) - 2:
            raise Exception("Too big TCP packet")
        return data[2:]

    def send_data(self, data):
        sz = struct.pack('>H', len(data))
        get_ip()
        return self.request.sendall(sz + data)


class UDPRequestHandler(BaseRequestHandler):

    def get_data(self):
        return self.request[0].strip()

    def send_data(self, data):
        get_ip()
        return self.request[1].sendto(data, self.client_address)


def main():
    log_to_file("server started")
    login_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
    log_to_file("Login time: {}", login_time)
    parser = argparse.ArgumentParser(description='Start a DNS implemented in Python.')
    parser = argparse.ArgumentParser(description='Start a DNS implemented in Python. Usually DNSs use UDP on port 53.')
    parser.add_argument('--port', default=5053, type=int, help='The port to listen on.')
    parser.add_argument('--tcp', action='store_true', help='Listen to TCP connections.')
    parser.add_argument('--udp', action='store_true', help='Listen to UDP datagrams.')
    
    args = parser.parse_args()
    if not (args.udp or args.tcp): parser.error("Please select at least one of --udp or --tcp.")

    print("Starting nameserver...")
    log_to_file("name server started")
    servers = []
    if args.udp: servers.append(socketserver.ThreadingUDPServer(('', args.port), UDPRequestHandler))
    if args.tcp: servers.append(socketserver.ThreadingTCPServer(('', args.port), TCPRequestHandler))

    for s in servers:
        thread = threading.Thread(target=s.serve_forever)  # that thread will start one more thread for each request
        thread.daemon = True  # exit the server thread when the main thread terminates
        thread.start()
        print("%s server loop running in thread: %s" % (s.RequestHandlerClass.__name__[:3], thread.name))

    try:
        while 1:
            time.sleep(1)
            sys.stderr.flush()
            sys.stdout.flush()

    except KeyboardInterrupt:
        pass
    finally:
        logout_time = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f')
        log_to_file("Logout time: {}", logout_time)

        for s in servers:
            log_to_file("Shutting Down Server...")
            s.shutdown()

        logging.info('\n')

if __name__ == '__main__':
    main()
