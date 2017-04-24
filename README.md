# switchmate
A python-based command line utility for controlling
[Switchmate](http://www.myswitchmate.com/) switches.

## Usage

	./switchmate.py scan
	./switchmate.py status [<mac_address>]
	./switchmate.py <mac_address> auth 
	./switchmate.py <mac_address> <auth_key> switch [on | off]

	$ sudo ./switchmate.py scan
	Scanning...
	Found Switchmates:
	ee:0d:eb:e4:3f:0d
	e4:ee:fc:66:48:aa
	c9:5e:b2:60:37:01

	$ sudo ./switchmate.py status
	Looking for switchmate status...
	ee:0d:eb:e4:3f:0d off
	e4:ee:fc:66:48:aa off
	c9:5e:b2:60:37:01 on

	$ sudo ./switchmate.py status ee:0d:eb:e4:3f:0d
	Looking for switchmate status...
	ee:0d:eb:e4:3f:0d off

	$ ./switchmate.py ee:0d:eb:e4:3f:0d auth
	Press button on Switchmate to get auth key
	Waiting for response...
	Auth key is 4723210F

	$ ./switchmate.py ee:0d:eb:e4:3f:0d 4723210F switch on
	Waiting for response
	Switched!

	$ ./switchmate.py ee:0d:eb:e4:3f:0d 4723210F switch off
	Waiting for response
	Switched!

**Note:** You cannot use this script and the Switchmate app simultaneously.

Based on code from [scottjg/switchmate](https://github.com/scottjg/switchmate).
