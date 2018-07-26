# switchmate

A python-based command line utility for controlling
[Switchmate](https://www.mysimplysmarthome.com/products/switchmate-switches/) switches.

## Usage

    ./switchmate.py scan [options]
    ./switchmate.py status [options]
    ./switchmate.py <mac_address> status [options]
    ./switchmate.py <mac_address> switch (on | off)
    ./switchmate.py <mac_address> toggle
    ./switchmate.py <mac_address> battery-level
    ./switchmate.py <mac_address> debug

	$ sudo ./switchmate.py scan
	Scanning...
	Found Switchmates:
	ee:0d:eb:e4:3f:0d
	e4:ee:fc:66:48:aa
	c9:5e:b2:60:37:01

	$ sudo ./switchmate.py status --timeout=10
	Looking for switchmate status...
	ee:0d:eb:e4:3f:0d off
	e4:ee:fc:66:48:aa off
	c9:5e:b2:60:37:01 on

	$ sudo ./switchmate.py ee:0d:eb:e4:3f:0d status
	Looking for switchmate status...
	ee:0d:eb:e4:3f:0d off

	$ sudo ./switchmate.py ee:0d:eb:e4:3f:0d switch on
	Switched!

	$ sudo ./switchmate.py ee:0d:eb:e4:3f:0d toggle
	Switched on!

	$ sudo ./switchmate.py ee:0d:eb:e4:3f:0d battery-level
	Battery level: 45%
