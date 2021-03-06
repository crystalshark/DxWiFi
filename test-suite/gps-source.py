#!/usr/bin/env python
from __future__ import print_function
from contextlib import contextmanager
import threading
import serial
import socket
import struct
import time

INFINITE_PACKETS = False
GPS_on = False
GPS_Data = ''
GPS_ttynum = 0

def gps_open():
    global GPS_on
    global GPS_ttynum
    try:
        #print('/dev/ttyUSB' + str(GPS_ttynum))
        GPS_Device = serial.Serial('/dev/ttyUSB' + str(GPS_ttynum), 9600, timeout=None)
        GPS_Device.write("$PMTK314,0,1,0,1,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0*28\r\n")
        GPS_Device.write("$PMTK220,200*2C\r\n")
        GPS_on = True
        return GPS_Device
    except:
        GPS_on = False
        if GPS_ttynum < 10:
            GPS_ttynum += 1
        else:
            GPS_ttynum = 0
        return 0

# Defines:
SEND_IP = b'192.168.0.255'
SEND_PORT = 12121
FROM_IP = b'0.0.0.0'
FROM_PORT = 21212

# Number packets to send
PACKET_S = 1000     # bytes
PACKET_N = 1000     # total number of packets to send

# Packet definition
PACKET = [
    {'fourcc': '0' * 2 + 'SEQN', 'struct': struct.Struct("!6s12s"), 'data': lambda: "%12d" % s},
    {'fourcc': 'TMST', 'struct': struct.Struct("!4s12s"), 'data': lambda: "%12u" % int(time.time())},
    {'fourcc': 'SIZE', 'struct': struct.Struct("!4s12s"), 'data': lambda: "%12u" % PACKET_S},
]

# calculate leftover size
def add_zeroes():
    size = 0
    for m in PACKET:
        size += m['struct'].size + len(GPS_Data)
    leftovers = chr(0)*(PACKET_S-size)
    return leftovers

# rate calc
packpersec = 125e3 / PACKET_S
delay = 1 / packpersec

@contextmanager
def udp():
    """UDP Socket creator as a context."""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    sock.bind((FROM_IP, FROM_PORT))
    sock.settimeout(0.1)
    yield sock
    sock.close()


def send(msg):
    with udp() as sock:
        sock.sendto(msg, (SEND_IP, SEND_PORT))

def sleepsafe(num):
    if num < 0:
        return 0
    return num

def readgps():
    global GPS_Data
    global GPS_on
    while 1:
        if GPS_on:
            try:
                current_line = GPS.readline()
            except:
                GPS_Data = ''
                GPS_on = False
            if '$GPGGA' in current_line and GPS_on == True:
                GPS_Data = current_line
        else:
            GPS = gps_open()

def start_gps_daemon():
    gps_raw = threading.Thread(target=readgps)
    gps_raw.daemon = True
    gps_raw.start()

if __name__ == '__main__':

    start_gps_daemon()
    s = 0
    packet_count = 0
    sendtime = time.time()
    while s < PACKET_N or INFINITE_PACKETS == True:
        zeroes = ''
        data = ''
        for m in PACKET:
            data += m['struct'].pack(m['fourcc'], m['data']())
        data += GPS_Data + add_zeroes()
        #print(data)
        sleeptime = sendtime + delay - time.time()
        if sleeptime > 0:
            time.sleep(sleeptime)
        send(data)
        sendtime = time.time()
        if s == 9999999:
            s = 0
        s += 1
