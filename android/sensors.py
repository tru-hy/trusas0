#!/usr/bin/env python

"""
A daemon to read Android sensors via SL4A
"""
import logging; log = logging.getLogger(__name__)
from trusas0.packing import ReprPack
import sys
from proxy import start_script_proxy

# Start the SL4A server

def read_events(proxy, output):
	"""Read the sensors until the end of the world which sends an interrupt"""

	while True:
		# This seems to be required for the event to be removed from	
		# the queue. There is the eventWaitFor, but I can't find a way
		# to remove the fetched event
		# :todo: Verify that this doesn't mess with other processes
		event = proxy.eventWait()
		result = event.result
		output.send(result['data'])


SENSOR_DELAY=0.01 # Minimum sensor delay in seconds
def main(sensor_delay=SENSOR_DELAY):

	proxy = start_script_proxy()
	log.info("SL5A server connected")

	# Start the sensors
	proxy.startSensingTimed(1, # All sensors
		int(sensor_delay*1000))

	output = ReprPack(sys.stdout)
	# :todo: If we can't clean up properly in every situation, the processes keep on
	# 	looping in the remote device and will bring it down at some point.
	#	A nicer way would be to have a separate server process for every instance
	#	and make sure it dies when we exit.
	try:
		read_events(proxy, output)
	except KeyboardInterrupt:
		pass
	finally:
		# :todo: We can't stop the SL4A server as it may be used by
		#	other processes
		proxy.stopSensing()

if __name__ == '__main__':
	main()
