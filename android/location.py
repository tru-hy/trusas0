#!/usr/bin/env python

"""
A daemon to read Android sensors via SL4A
"""
from trusas0.packing import ReprPack
from trusas0.utils import register_shutdown, get_logger
log = get_logger()
import sys
from proxy import start_script_proxy
import atexit
import signal

def read_events(proxy, output):
	"""Read the location until the end of the world which sends an interrupt"""

	while True:
		# This seems to be required for the event to be removed from	
		# the queue. There is the eventWaitFor, but I can't find a way
		# to remove the fetched event
		# :todo: Verify that this doesn't mess with other processes
		try:
			event = proxy.eventWait()
		except AttributeError:
			# This gets thrown because we sadistically kill
			# the socket in the shutdown, so demote to warning
			log.warning(
			"The location service died. If you were stopping "\
			"the session, it's nothing to worry about, the bug is "\
			"known and isn't dangerous, but keeps nagging so "\
			"that Jami will fix it some day.")
			return
		
		result = event.result
		if result is None: return
		output.send(result['data'])


def main(time_delay=10, distance_delay=0):
	proxy = start_script_proxy()
	output = ReprPack(sys.stdout)
	
	@register_shutdown
	def stop():
		# This is not very nice as it will
		# cause an exception in read_events,
		# but this thing is quite hacky anyhow
		proxy.client.close()
		tmp_proxy = start_script_proxy()
		tmp_proxy.stopLocating()
		tmp_proxy.client.close()
	
	proxy.startLocating(time_delay, distance_delay)
	read_events(proxy, output)
	
	

if __name__ == '__main__':
	main()
