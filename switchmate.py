#! /usr/bin/env python

"""switchmate.py

A python-based command line utility for controlling Switchmate switches.

Usage:
    ./switchmate.py scan [options]
    ./switchmate.py status [options]
    ./switchmate.py <mac_address> status [options]
    ./switchmate.py <mac_address> switch (on | off)
    ./switchmate.py <mac_address> toggle
    ./switchmate.py <mac_address> battery-level
    ./switchmate.py <mac_address> debug
    ./switchmate.py (-h | --help) | help

Commands:
    scan
        Scan for switchmate devices and print their mac addresses.
    status
        Scan for switchmate devices and print their mac addresses and status.
    switch (on | off)
        Switch a device on or off.
    toggle
        Switch a device on if currently off, or off if currently on.
    debug
        Print a detailed information about a device, for debugging purposes.
    help
        Show this help screen.

Options:
    -t <seconds>, --timeout=<seconds>  [default: 2]
        Search for devices until this timeout.
    -h, --help
        Show this help screen.
"""

from __future__ import print_function
import sys

from docopt import docopt
from bluepy.btle import (
    Scanner, Peripheral, AssignedNumbers,
    ADDR_TYPE_RANDOM, UUID, BTLEException
)
from binascii import hexlify
from tabulate import tabulate


def identity(x):
    return x


if sys.version_info >= (3,):
    # In Python 3 we are already dealing with bytes,
    # so just return the original value.
    get_byte = identity
else:
    get_byte = ord

# firmware == 2.99.15 (or higher?)
SWITCHMATE_SERVICE = 'a22bd383-ebdd-49ac-b2e7-40eb55f5d0ab'

ORIGINAL_STATE_HANDLE = 0x2e
BRIGHT_STATE_HANDLE = 0x30

ORIGINAL_MODEL_STRING_HANDLE = 0x14

SERVICES_AD_TYPE = 0x07
MANUFACTURER_DATA_AD_TYPE = 0xff


def get_switchmates(scan_entries, mac_address):
    switchmates = []
    for scan_entry in scan_entries:
        service_uuid = scan_entry.getValueText(SERVICES_AD_TYPE)
        is_switchmate = service_uuid == SWITCHMATE_SERVICE
        if not is_switchmate:
            continue
        if mac_address and scan_entry.addr == mac_address:
            return [scan_entry]
        if scan_entry not in switchmates:
            switchmates.append(scan_entry)
    switchmates.sort(key=lambda sw: sw.addr)
    return switchmates


def scan(
    start_msg, process_entry,
    timeout=None, mac_address=None, success_msg=None
):
    print(start_msg)
    sys.stdout.flush()

    scanner = Scanner()

    try:
        switchmates = get_switchmates(scanner.scan(timeout), mac_address)
    except BTLEException as ex:
        print(
            'ERROR: Could not complete scan.',
            'Try running switchmate with sudo.',
            ex.message
        )
        return
    except OSError as ex:
        print(
            'ERROR: Could not complete scan.',
            'Try compiling the bluepy helper.',
            ex
        )
        return

    if len(switchmates):
        if success_msg:
            print(success_msg)
        for switchmate in switchmates:
            process_entry(switchmate)
    else:
        print('No Switchmate devices found')


def debug_helper(device):
    output = [['uuid', 'common name', 'handle', 'properties', 'value']]
    for char in device.getCharacteristics():
        if char.supportsRead():
            val = char.read()
            binary = False
            for c in val:
                if get_byte(c) < 32 or get_byte(c) > 126:
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


def is_original_device(device):
    # The handle for reading the model string on Bright devices is actually
    # different from Original devices, but using getCharacteristics to read
    # the model is much slower.
    model = device.readCharacteristic(ORIGINAL_MODEL_STRING_HANDLE)
    return model == b'Original'


def get_state_handle(device):
    if is_original_device(device):
        return ORIGINAL_STATE_HANDLE
    else:
        return BRIGHT_STATE_HANDLE


def switch(device, val):
    state_handle = get_state_handle(device)
    curr_val = device.readCharacteristic(state_handle)
    if val is None:
        val = b'\x01' if curr_val == b'\x00' else b'\x00'
    val_num = get_byte(val[0])
    val_text = ('off', 'on')[val_num]
    if curr_val != val:
        device.writeCharacteristic(state_handle, val, True)
        print('Switched {}!'.format(val_text))
    else:
        print('Already {}!'.format(val_text))


def print_entry_state(entry, state_handle=None):
    service_data = entry.getValueText(MANUFACTURER_DATA_AD_TYPE)
    val = int(service_data[1])
    print(entry.addr, ("off", "on")[val])


def print_battery_level(device):
    battery_level = AssignedNumbers.batteryLevel
    level = device.getCharacteristics(uuid=battery_level)[0].read()
    print('Battery level: {}%'.format(ord(level)))


def print_exception(ex):
    if 'disconnected' in ex.message.lower():
        print('ERROR: Device disconnected.')
    else:
        print('ERROR: ' + ex.message)


if __name__ == '__main__':
    arguments = docopt(__doc__)

    if arguments['help']:
        print(__doc__)
        sys.exit()

    timeout = int(arguments['--timeout'])

    if arguments['scan']:
        scan(
            'Scanning...',
            success_msg='Found Switchmates:',
            timeout=timeout,
            process_entry=lambda switchmate: print(switchmate.addr),
        )
        sys.exit()

    mac_address = arguments['<mac_address>']
    if arguments['status']:
        scan(
            'Looking for switchmate status...',
            timeout=timeout,
            process_entry=print_entry_state,
            mac_address=mac_address,
        )
        sys.exit()

    try:
        device = Peripheral(mac_address, ADDR_TYPE_RANDOM)
    except BTLEException as ex:
        if 'failed to connect' in ex.message.lower():
            print(
                'ERROR: Failed to connect to device.',
                'Try running switchmate with sudo.',
            )
        else:
            print('ERROR: ' + ex.message)
        sys.exit(1)
    except OSError as ex:
        print(
            'ERROR: Failed to connect to device.',
            'Try compiling the bluepy helper.',
            ex
        )
        sys.exit(1)

    if arguments['debug']:
        try:
            print('Retrieving debug info...')
            debug_helper(device)
            device.disconnect()
        except Exception as ex:
            print('ERROR: Could not retrieve debug info.', ex.message)
            sys.exit(1)
        else:
            sys.exit()

    if arguments['switch'] or arguments['toggle']:
        if arguments['on']:
            val = b'\x01'
        else:
            val = b'\x00'
        if arguments['toggle']:
            val = None
        try:
            switch(device, val)
        except BTLEException as ex:
            print_exception(ex)
            sys.exit(1)

    if arguments['battery-level']:
        try:
            print_battery_level(device)
        except BTLEException as ex:
            print_exception(ex)
            sys.exit(1)
