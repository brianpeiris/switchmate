#! /usr/bin/env python

"""switchmate.py

A python-based command line utility for controlling Switchmate switches

Usage:
	./switchmate.py scan
	./switchmate.py status
	./switchmate.py <mac_address> auth
	./switchmate.py <mac_address> <auth_key> switch [on | off]
	./switchmate.py -h | --help
"""

#from __future__ import print_function
import struct
import sys
import ctypes

from time import time

from docopt import docopt
from bluepy.btle import Scanner, DefaultDelegate, Peripheral, ADDR_TYPE_RANDOM
from binascii import hexlify, unhexlify

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
		if handle == AUTH_HANDLE:
			print('Auth key is {}'.format(hexlify(data[3:]).upper()))
		else:
			print('Switched!')
		device.disconnect()
		sys.exit()

class ScanDelegate(DefaultDelegate):
	def __init__(self):
		DefaultDelegate.__init__(self)

	def handleDiscovery(self, dev, isNewDev, isNewData):
		AD_TYPE_UUID = 0x07
		SWITCHMATE_UUID = '23d1bcea5f782315deef121223150000'

		AD_TYPE_SERVICE_DATA = 0x16

		if (dev.getValueText(AD_TYPE_UUID) == SWITCHMATE_UUID):
			data = dev.getValueText(AD_TYPE_SERVICE_DATA)
			# the bit at 0x0100 signifies if the switch is off or on
			print time(), ("off", "on")[(int(data, 16) >> 8) & 1]

def status():
	print('Looking for switchmate status...')
	sys.stdout.flush()

	scanner = Scanner().withDelegate(ScanDelegate())

	scanner.clear()
	scanner.start()
	scanner.process(30.0)
	scanner.stop()

def scan():
	print('Scanning...')
	sys.stdout.flush()

	scanner = Scanner()
	devices = scanner.scan(10.0)

	SERVICES_AD_TYPE = 7
	SWITCHMATE_SERVICE = '23d1bcea5f782315deef121223150000'

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
		status()
		sys.exit()

	device = Peripheral(arguments['<mac_address>'], ADDR_TYPE_RANDOM)

	notifications = NotificationDelegate()
	device.setDelegate(notifications)

	if arguments['switch']:
		auth_key = unhexlify(arguments['<auth_key>'])
		device.writeCharacteristic(STATE_NOTIFY_HANDLE, NOTIFY_VALUE, True)
		if arguments['on']:
			val = '\x01'
		else:
			val = '\x00'
		device.writeCharacteristic(STATE_HANDLE, sign('\x01' + val, auth_key))
	else:
		device.writeCharacteristic(AUTH_NOTIFY_HANDLE, NOTIFY_VALUE, True)
		device.writeCharacteristic(AUTH_HANDLE, AUTH_INIT_VALUE, True)
		print('Press button on Switchmate to get auth key')

	print('Waiting for response')
	while True:
		device.waitForNotifications(1.0)
		print('.')
		sys.stdout.flush()
