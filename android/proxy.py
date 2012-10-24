import time
import socket
import logging; log = logging.getLogger(__name__)
from trusas0.utils import sh, ShellError

from android import Android


# The ADB binary path
ADB = "adb"
# The port for SL4A
SL4A_PORT = 5556
# The host (PC) port for the TCP forwarding
HOST_PORT = 5556
# The remote (Android) port for the TCP forwarding
REMOTE_PORT = 5556

START_MESSAGE = "New trusas0 connection"


def start_script_proxy(toast_message=START_MESSAGE, server_wait=1.0, retries=10):

	adb = lambda cmd, ADB=ADB: sh("%s %s"%(ADB, cmd))

	# Start TCP forwarding
	adb("forward tcp:%i tcp:%i"%(HOST_PORT, REMOTE_PORT))


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
		


logging.basicConfig(level=logging.DEBUG)
