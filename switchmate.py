#! /usr/bin/env python

"""switchmate.py

A python-based command line utility for controlling Switchmate switches.

Usage:
    ./switchmate.py scan
    ./switchmate.py status [<mac_address>]
    ./switchmate.py <mac_address> debug
    ./switchmate.py <mac_address> auth
    ./switchmate.py <mac_address> (<auth_key> | none) switch [on | off]
    ./switchmate.py -h | --help

Note: Newer switchmate devices/firmwares do not require auth keys.
Simply specify 'none', instead of the auth key, when invoking the
switch command.
"""

from __future__ import print_function
import struct
import sys
import ctypes

from docopt import docopt
from bluepy.btle import (Scanner, DefaultDelegate, Peripheral,
    ADDR_TYPE_RANDOM, UUID, BTLEException)
from binascii import hexlify, unhexlify
from tabulate import tabulate
from time import sleep

def noop(x):
    return x

if sys.version_info >= (3,):
    long = int
    ord = noop

# firmware < 2.99.15
OLD_FIRMWARE_SERVICE = '23d1bcea5f782315deef121223150000'
# firmware == 2.99.15 (or higher?)
NEW_FIRMWARE_SERVICE = 'abd0f555eb40e7b2ac49ddeb83d32ba2'

SWITCHMATE_SERVICES = [
    OLD_FIRMWARE_SERVICE,
    NEW_FIRMWARE_SERVICE,
]

NOTIFY_VALUE = '\x01'

AUTH_NOTIFY_HANDLE = 0x17
AUTH_HANDLE = 0x16
AUTH_INIT_VALUE = '\x00\x00\x00\x00\x01\x00'

STATE_HANDLE = 0x0e
STATE_NOTIFY_HANDLE = 0x0f
NEW_STATE_HANDLE = 0x2e

SERVICES_AD_TYPE = 0x07

def c_mul(a, b):
    '''
    Multiplication function with overflow
    '''
    return ctypes.c_int64((long(a) * b) &0xffffffffffffffff).value

def sign(data, key):
    '''
    Variant of the Fowler-Noll-Vo (FNV) hash function
    '''
    blob = data + key
    x = ord(blob[0]) << 7
    for c in blob:
        x1 = c_mul(1000003, x)
        x = x1 ^ ord(c) ^ len(blob)

    # once we have the hash, we append the data
    shifted_hash = (x & 0xffffffff) << 16
    shifted_data_0 = ord(data[0]) << 48
    shifted_data_1 = ord(data[1]) << 56
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
            if ord(data[-1]) == 0:
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

        AD_TYPE_SERVICE_DATA = 0x16
        service = dev.getValueText(SERVICES_AD_TYPE)
        val = None
        if service == OLD_FIRMWARE_SERVICE:
            data = dev.getValueText(AD_TYPE_SERVICE_DATA)
            # the bit at 0x0100 signifies if the switch is off or on
            val = (int(data, 16) >> 8) & 1
        elif service == NEW_FIRMWARE_SERVICE:
            try:
                peripheral = Peripheral(dev.addr, ADDR_TYPE_RANDOM)
                val = ord(peripheral.readCharacteristic(NEW_STATE_HANDLE)[0])
            except Exception as ex:
                print('WARNING: Could not read status of {}. {}'.format(dev.addr, ex.message))

        if val is not None:
            print(dev.addr + ' ' + ("off", "on")[val])
            if self.mac_address != None:
                sys.exit()


def status(mac_address):
    print('Looking for switchmate status...')
    sys.stdout.flush()

    scanner = Scanner().withDelegate(ScanDelegate(mac_address))

    try:
        scanner.clear()
        scanner.start()
        scanner.process(5)
        scanner.stop()
    except BTLEException as ex:
        print('WARNING: Scanning interrupted. {}'.format(ex.message))

def scan():
    print('Scanning...')
    sys.stdout.flush()

    scanner = Scanner()
    devices = scanner.scan(10.0)

    switchmates = []
    for dev in devices:
        for (adtype, desc, value) in dev.getScanData():
            is_switchmate = adtype == SERVICES_AD_TYPE and value in SWITCHMATE_SERVICES
            if is_switchmate and dev not in switchmates:
                switchmates.append(dev)

    if len(switchmates):
        print('Found Switchmates:')
        for switchmate in switchmates:
            print(switchmate.addr)
    else:
        print('No Switchmate devices found');

def debug_helper(device):
    output = [['uuid', 'common name', 'handle', 'properties', 'value']]
    for char in device.getCharacteristics():
        if char.supportsRead():
            val = char.read()
            binary = False
            for c in val:
                if ord(c) < 32 or ord(c) > 126:
                    binary = True
            if binary:
                val = hexlify(val)
        output.append([
            str(char.uuid),
            UUID(char.uuid).getCommonName(),
            '{0:x}'.format(char.getHandle()),
            char.propertiesToString(),
            str(val)
        ])
    print(tabulate(output, headers='firstrow'))


if __name__ == '__main__':
    arguments = docopt(__doc__)

    if arguments['scan']:
        try: 
            scan()
        except BTLEException as ex:
            print('ERROR: Could not complete scan. Try running switchmate with sudo. {}'.format(ex.message))
        except OSError as ex:
            print('ERROR: Could not complete scan. Try compiling the bluepy helper. {}'.format(ex))
        sys.exit()

    mac_address = arguments['<mac_address>']
    if arguments['status']:
        status(mac_address)
        sys.exit()

    try:
        device = Peripheral(mac_address, ADDR_TYPE_RANDOM)
    except BTLEException as ex:
        if 'failed to connect' in ex.message.lower():
            print('ERROR: Failed to connect to device.')
        else:
            print('ERROR: ' + ex.message)
        sys.exit(1)

    if arguments['debug']:
        try:
            print('Retrieving debug info...')
            debug_helper(device)
        except Exception as ex:
            print('ERROR: Could not retrieve debug info. {}'.format(ex.message))
            sys.exit(1)
        else:
            sys.exit()

    device.setDelegate(NotificationDelegate())

    if arguments['on']:
        val = b'\x01'
    else:
        val = b'\x00'

    try:
        if arguments['switch'] and arguments['<auth_key>'] == 'none':
            device.writeCharacteristic(NEW_STATE_HANDLE, val, True)
            print('Switched!')
        elif arguments['switch']:
            auth_key = unhexlify(arguments['<auth_key>'])
            device.writeCharacteristic(STATE_NOTIFY_HANDLE, '\x01', True)
            device.writeCharacteristic(STATE_HANDLE, sign('\x01' + val, auth_key))
            print('Waiting for response', end='')
            while True:
                device.waitForNotifications(1.0)
                print('.', end='')
                sys.stdout.flush()
        else:
            device.writeCharacteristic(AUTH_NOTIFY_HANDLE, NOTIFY_VALUE, True)
            device.writeCharacteristic(AUTH_HANDLE, AUTH_INIT_VALUE, True)
            print('Press button on Switchmate to get auth key')
    except BTLEException as ex:
        if 'disconnected' in ex.message.lower():
            print('ERROR: Device disconnected.')
        else:
            print('ERROR: ' + ex.message);
        sys.exit(1)
