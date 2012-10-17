#!/usr/bin/env python

"""
A daemon to read Android sensors via SL4A
"""
import logging; log = logging.getLogger(__name__)
from trusas0.utils import sh, ShellError
from trusas0.packing import ReprPack
import sys
from android import Android
import time
import socket

logging.basicConfig(level=logging.DEBUG)

# The ADB binary path
ADB = "adb"
# The port for SL4A
SL4A_PORT = 5555
# The host (PC) port for the TCP forwarding
HOST_PORT = 5555
# The remote (Android) port for the TCP forwarding
REMOTE_PORT = 5555

SENSOR_DELAY=0.01 # Minimum sensor delay in seconds

START_MESSAGE = "New trusas0 connection"

output = ReprPack(sys.stdout)



adb = lambda cmd, ADB=ADB: sh("%s %s"%(ADB, cmd))

# Start TCP forwarding
adb("forward tcp:%i tcp:%i"%(HOST_PORT, REMOTE_PORT))



def start_script_proxy(toast_message, server_wait=1.0, retries=10):
	proxy = Android(addr=(None, HOST_PORT))
	start_message = lambda: proxy.makeToast(toast_message)

	try:
		# Try if we are already connected SL4A will start the server with
		# a random port if it's already running regardless of the
		# USE_SERVICE_PORT parameter
		start_message()
		return proxy # We seem to be connected
	except socket.error, e:
		# Try to start the server
		adb("shell am start "
		    "-a com.googlecode.android_scripting.action.LAUNCH_SERVER "
		    "-n com.googlecode.android_scripting/.activity.ScriptingLayerServiceLauncher "
		    "--ei com.googlecode.android_scripting.extra.USE_SERVICE_PORT %i"%SL4A_PORT)
	
	# :TODO: Get rid of the hacky asynchronous SL4A startup
	for i in range(retries):
		proxy = Android(addr=(None, HOST_PORT))
		try:
			start_message()
			break # We seem to be connected
		except socket.error, e:
			log.debug("SL4A retry: "+str(e))
		
		time.sleep(server_wait)
	else:
		raise IOError("Unable to start SL4A server")

	return proxy
		

# Start the SL4A server
proxy = start_script_proxy(START_MESSAGE)
log.info("SL5A server connected")

# Start the sensors
proxy.startSensingTimed(1, # All sensors
		int(SENSOR_DELAY*1000))

def read_events():
	"""Read the sensors until the end of the world which sends an interrupt"""

	while True:
		# This seems to be required for the event to be removed from	
		# the queue. There is the eventWaitFor, but I can't find a way
		# to remove the fetched event
		# :todo: Verify that this doesn't mess with other processes
		event = proxy.eventWait()
		result = event.result
		output.send(result['data'])

# :todo: If we can't clean up properly in every situation, the processes keep on
# 	looping in the remote device and will bring it down at some point.
#	A nicer way would be to have a separate server process for every instance
#	and make sure it dies when we exit.
try:
	read_events()
except KeyboardInterrupt:
	pass
finally:
	# :todo: We can't stop the SL4A server as it may be used by
	#	other processes
	proxy.stopSensing()
