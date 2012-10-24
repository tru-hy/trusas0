#!/usr/bin/env python

"""
A daemon to read Android sensors via SL4A
"""
import logging; log = logging.getLogger(__name__)
from trusas0.packing import ReprPack
import sys
from proxy import start_script_proxy

def read_events(proxy, output):
	"""Read the location until the end of the world which sends an interrupt"""

	while True:
		# This seems to be required for the event to be removed from	
		# the queue. There is the eventWaitFor, but I can't find a way
		# to remove the fetched event
		# :todo: Verify that this doesn't mess with other processes
		event = proxy.eventWait()
		result = event.result
		output.send(result['data'])


def main(time_delay=10, distance_delay=0):
	proxy = start_script_proxy()
	output = ReprPack(sys.stdout)
	
	proxy.startLocating(time_delay, distance_delay)
	try:
		read_events(proxy, output)
	except KeyboardInterrupt:
		pass
	finally:
		proxy.stopLocating()
	
	

if __name__ == '__main__':
	main()
