# switchmate
A python-based command line utility for controlling 
[Switchmate](https://github.com/scottjg/switchmate) switches.

## Usage

	./switchmate.py auth <mac_address>
	./switchmate.py switch <mac_address> <auth_key> [on | off]

	> ./switchmate EE:0D:EB:E4:3F:0D auth
	Press button on Switchmate to get auth key
	Waiting for response...
	Auth key is 4723210F
	> ./switchmate EE:0D:EB:E4:3F:0D 4723210F switch on
	Waiting for response
	Switched!
	> ./switchmate EE:0D:EB:E4:3F:0D 4723210F switch off
	Waiting for response
	Switched!
	

Based on code from [scottjg/switchmate](https://github.com/scottjg/switchmate).
