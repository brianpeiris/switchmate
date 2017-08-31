#! /usr/bin/env python

"""switchmate.py

A python-based command line utility for controlling Switchmate switches

Usage:
    ./switchmate.py scan
    ./switchmate.py status [<mac_address>]
    ./switchmate.py <mac_address> auth
    ./switchmate.py <mac_address> <auth_key> switch [on | off]
    ./switchmate.py -h | --help
"""

from __future__ import print_function
import struct
import sys
import ctypes

from docopt import docopt
from bluepy.btle import (
    Scanner, DefaultDelegate, Peripheral, ADDR_TYPE_RANDOM, BTLEException)
from binascii import hexlify, unhexlify

SWITCHMATE_SERVICE = '23d1bcea5f782315deef121223150000'
NOTIFY_VALUE = struct.pack('<BB', 0x01, 0x00)

AUTH_NOTIFY_HANDLE = 0x0017
AUTH_HANDLE = 0x0016
AUTH_INIT_VALUE = struct.pack('<BBBBBB', 0x00, 0x00, 0x00, 0x00, 0x01, 0x00)

STATE_HANDLE = 0x000e
STATE_NOTIFY_HANDLE = 0x000f

def c_mul(a, b):
    '''
    Multiplication function with overflow
    '''
    return ctypes.c_int64((a * b) &0xffffffffffffffff).value

def sign(data, key):
    '''
    Variant of the Fowler-Noll-Vo (FNV) hash function
    '''
    blob = data + key
    x = blob[0] << 7
    for c in blob:
        x1 = c_mul(1000003, x)
        x = x1 ^ c ^ len(blob)

    # once we have the hash, we append the data
    shifted_hash = (x & 0xffffffff) << 16
    shifted_data_0 = data[0] << 48
    shifted_data_1 = data[1] << 56
    packed = struct.pack('<Q', shifted_hash | shifted_data_0 | shifted_data_1)[2:]
    return packed

class NotificationDelegate(DefaultDelegate):
    def __init__(self):
        DefaultDelegate.__init__(self)

    def handleNotification(self, handle, data):
        print('')
        succeeded = True
        if handle == AUTH_HANDLE:
            print('Auth key is {}'.format(hexlify(data[3:]).upper()))
        else:
            if data[-1] == 0:
                print('Switched!')
            else:
                print('Switching failed!')
                succeeded = False
        device.disconnect()
        sys.exit(0 if succeeded else 1)

class ScanDelegate(DefaultDelegate):
    def __init__(self, mac_address):
        DefaultDelegate.__init__(self)
        self.mac_address = mac_address
        self.seen = []

    def handleDiscovery(self, dev, isNewDev, isNewData):
        if self.mac_address != None and self.mac_address != dev.addr:
            return

        if dev.addr in self.seen:
            return
        self.seen.append(dev.addr)

        AD_TYPE_UUID = 0x07
        AD_TYPE_SERVICE_DATA = 0x16
        if dev.getValueText(AD_TYPE_UUID) == SWITCHMATE_SERVICE:
            data = dev.getValueText(AD_TYPE_SERVICE_DATA)
            # the bit at 0x0100 signifies if the switch is off or on
            print(dev.addr + ' ' + ("off", "on")[(int(data, 16) >> 8) & 1])
            if self.mac_address != None:
                sys.exit()

def status(mac_address):
    print('Looking for switchmate status...')
    sys.stdout.flush()

    scanner = Scanner().withDelegate(ScanDelegate(mac_address))

    scanner.clear()

    try:
        scanner.start()
        scanner.process(20)
        scanner.stop()
    except BTLEException:
        pass

def scan():
    print('Scanning...')
    sys.stdout.flush()

    scanner = Scanner()
    devices = scanner.scan(10.0)

    SERVICES_AD_TYPE = 7

    switchmates = []
    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            is_switchmate = adtype == SERVICES_AD_TYPE and value == SWITCHMATE_SERVICE
            if is_switchmate and dev not in switchmates:
                switchmates.append(dev)

    if len(switchmates):
        print('Found Switchmates:')
        for switchmate in switchmates:
            print(switchmate.addr)
    else:
        print('No Switchmate devices found');

if __name__ == '__main__':
    arguments = docopt(__doc__)

    if arguments['scan']:
        scan()
        sys.exit()

    if arguments['status']:
        status(arguments['<mac_address>'])
        sys.exit()

    device = Peripheral(arguments['<mac_address>'], ADDR_TYPE_RANDOM)

    notifications = NotificationDelegate()
    device.setDelegate(notifications)

    if arguments['switch']:
        auth_key = unhexlify(arguments['<auth_key>'])
        device.writeCharacteristic(STATE_NOTIFY_HANDLE, NOTIFY_VALUE, True)
        if arguments['on']:
            val = b'\x01\x01'
        else:
            val = b'\x01\x00'
        device.writeCharacteristic(STATE_HANDLE, sign(val, auth_key))
    else:
        device.writeCharacteristic(AUTH_NOTIFY_HANDLE, NOTIFY_VALUE, True)
        device.writeCharacteristic(AUTH_HANDLE, AUTH_INIT_VALUE, True)
        print('Press button on Switchmate to get auth key')

    print('Waiting for response', end='')
    while True:
        device.waitForNotifications(1.0)
        print('.', end='')
        sys.stdout.flush()
