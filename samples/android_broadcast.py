#!/usr/bin/env python
import logging; log = logging.getLogger(__name__)
from trusas0.android_sensors.startup import *

ADB_PORT=5555

# Enable this if you want to do ADB over network
#DEVICE_HOST="192.168.1.140"


ADB_PATH="adb"

def main():
	# Let's get some spam
	logging.basicConfig(level=logging.DEBUG)
	
		connect_adb_over_network(
			host=DEVICE_HOST, # Hostname or IP of the android device
			port=ADB_PORT, # Port that the device is running
			adb_path=adb_path)

	android = start_proxy_via_adb(
		# Assumes ADB is in PATH
		adb_path="adb",
		# You will probably need to start the
		# ADB socket forwarding (adb forward) for localhost
		adb_host=ADB_HOST,
		adb_port=ADB_PORT,
		)
	
	


if __name__ == '__main__':
	main()
