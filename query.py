from bluepy.btle import DefaultDelegate, Peripheral, ADDR_TYPE_RANDOM
from binascii import hexlify

device = Peripheral('EE:0D:EB:E4:3F:0D', ADDR_TYPE_RANDOM)
for sr in device.getServices():
	print(sr.uuid.getCommonName())
	for ch in sr.getCharacteristics():
		print(ch.uuid.getCommonName(), '%02x' % ch.getHandle(), ch.propertiesToString())
