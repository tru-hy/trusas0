#!/usr/bin/env python2

#!/usr/bin/env python2

# TODO! Almost full copypaste from sensors.py!

from trusas0.utils import sh, relative, get_logger
#log = get_logger()
from trusas0.packing import default_packer
import sys
import subprocess
from os import path
import socket
from StringIO import StringIO
import time
from itertools import chain
import json

LOCATION_PORT = 27546
ADB = "adb"
SERVER_APK = relative("java/TrusasSensorDump.apk")

class SocketLineReader(object):
	def __init__(self, con, bufsize=4096):
		self.con = con
		# Would have used StringIO, but it does quite weird
		# stuff having buflist and buf and messing around with
		# those, so I don't trust it
		self.buflist = []
		self.bufsize = bufsize
	
	def has_eof(self):
		try:
			line = self.next()
		except StopIteration:
			return True

		#self.unread(line)
		return False

	def unread(self, data):
		self.buflist.insert(0, data.strip()+"\n")
	
	def next_line(self):
		# TODO: Ugly copypaste from logutils.py
		line_delim = '\n' # TODO: There may be a more portable way for this
		buflist = self.buflist
		for i, buf in enumerate(buflist):
			if line_delim in buf:
				break
		else:
			return None

		last, not_ours = buflist[i].split(line_delim, 1)
		line = "".join(chain(buflist[:i], [last]))
		self.buflist = [not_ours] + buflist[i+1:]
		return line

	def __iter__(self): return self

	def next(self):
		while True:
			line = self.next_line()
			if line is not None:
				return line
			
			data = self.con.recv(self.bufsize)
			if data == '':
				# NOTE: There may still be data (without a newline)
				#	in the buffer,
				#	but the caller is probably only
				#	interested in full lines. If not, they
				#	can dig the remains from buf. Not gonna
				#	set up an extra flag just for this.
				raise StopIteration
			self.buflist.append(data)


def main(retries=10, retry_delay=0.5):
	adb = lambda cmd, ADB=ADB: sh("%s %s"%(ADB, cmd))
	adb("forward tcp:%i tcp:%i"%(LOCATION_PORT, LOCATION_PORT))
	adb("install %s"%SERVER_APK)
	adb("shell am startservice -a independent.trusas.LocationDumpManager")
	
	for retry in range(retries):
		try:
			con = socket.create_connection(
				("127.0.0.1", LOCATION_PORT),
				timeout=retry_delay)
			con.setblocking(1) # Just in case
			reader = SocketLineReader(con)
			# Seems to be the only way to see if the
			# socket is still (or in this case has ever really been)
			# connected.
			if not reader.has_eof():
				break
			
		except socket.error:
			pass
		
		time.sleep(retry_delay)
	else:
		raise IOError("Unable to connect to trusas location dump.")
	
	packer = default_packer()
	for line in reader:
		event = json.loads(line)
		packer.send(event)

if __name__ == '__main__':
	main()
