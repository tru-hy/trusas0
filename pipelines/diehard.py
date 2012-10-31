from subprocess import Popen
import os
from os import path
import sys
import time
import signal

SERVICE_VAR="TRUSAS_SERVICE"
POLL_INTERVAL=0.1

def bury_child(*args):
	# Just ignore the return value so that
	# it can be removed from the process table.
	# This way the pid-polling is same regardless of
	# whether the process is our child or not
	os.wait()
signal.signal(signal.SIGCHLD, bury_child)

def get_process_environment(pid, proc_dir):
	env_path = path.join(proc_dir, str(pid), 'environ')
	with open(env_path, 'r') as env_file:
		return env_file.read().split('\0')

def find_service(name, proc_dir='/proc'):
	service_name = "%s=%s"%(SERVICE_VAR, name)
	for pid in os.listdir(proc_dir):
		try:
			pid = int(pid)
		except ValueError:
			continue
		
		try:
			env = get_process_environment(pid, proc_dir)
		except IOError:
			continue
		
		if service_name in env:
			return pid
	
	return None

def start_service(name, command, stdout_fd, stderr_fd):
	pid = os.fork()
	if pid != 0:
		return pid
	
	#sys.stdout = open(stdout_file, 'w')
	#sys.stderr = open(stderr_file, 'w')
	os.dup2(stdout_fd, 1)
	os.dup2(stderr_fd, 2)
	os.putenv(SERVICE_VAR, name)
	os.setsid()
	os.execvp(command[0], command)

def ensure_service(name, command, stdout_file, stderr_file):
	pid = find_service(name)
	if pid:
		print "Reattaching"
		return pid

	print "Starting new service"
	# TODO: Don't overwrite!?
	stdout = open(stdout_file, 'w')
	stderr = open(stderr_file, 'w')
	pid = start_service(name, command,
		stdout.fileno(), stderr.fileno())
	stdout.close()
	stderr.close()
	return pid

pid = ensure_service("nexus", ("../nexus/physiology.py", "00:A0:96:2F:A8:A6"),
		"/tmp/nexus.data", "/tmp/nexus.log")

while True:
	try:
		os.kill(pid, 0)
	except OSError:
		print "The MF died!"
		break
	time.sleep(0.1)
