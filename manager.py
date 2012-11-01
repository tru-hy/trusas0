from subprocess import Popen
import os
from os import path
import sys
import time
import signal
import shlex

SERVICE_VAR="TRUSAS_SERVICE"

class ServiceException(Exception): pass
class ServiceNotFound(ServiceException): pass

class Service(object):
	def __init__(self, command, outfile, errfile):
		self.command = command
		self.outfile = outfile
		self.errfile = errfile

class ServiceManager(object):
	def __init__(self, base_dir, poll_interval=0.1):
		self.services = {}
		self.pids = {}
		self.base_dir = base_dir
		self.poll_interval = poll_interval

	def add(self, name, command, outfile=None, errfile=None):
		if name in self.services:
			raise ServiceException("Service '%s' already registered."%name)
		
		if outfile is None:
			outfile = path.join(self.base_dir, "%s.out"%outfile)
		if errfile is None:
			errfile = path.join(self.base_dir, "%s.err"%errfile)
		
		if isinstance(command, basestring):
			command = shlex.split(command)
		
		service = Service(command, outfile, errfile)
		self.services[name] = service

	def __setitem__(self, name, command):
		self.add(name, command)

	def __getitem__(self, name):
		return self.services[name]
		
	def start(self):
		signal.signal(signal.SIGCHLD, bury_child)
		for name in self.services:
			self.start_service(name)

	def start_service(self, name):
		service = self.services[name]
		pid = ensure_service(name, service.command,
			service.outfile, service.errfile)
		self.pids[name] = pid


	def is_running(self, name):
		try:
			pid = self.pids[name]
		except KeyError:
			raise ServiceException("Service '%s' not registered."%name)

		return pid_is_running(pid)

	def dead_services(self):
		return [name for name in self.services
			if not self.is_running(name)]

	def start_monitoring(self):
		while True:
			dead = dead_services()
			if len(dead) > 0:
				print "Dead services %s"%(dead,)
			time.sleep(self.poll_interval)
	
def pid_is_running(pid):
	try:
		os.kill(pid, 0)
	except OSError:
		# :todo: The OSError may be in theory for other reasons
		#	than ESRCH
		return False

	return True


def ensure_service(name, command, stdout_file, stderr_file):
	try:
		pid = find_service(name)
		print "Reattaching"
	except ServiceNotFound:
		pass
	else:
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


def bury_child(*args):
	# Just ignore the return value so that
	# it can be removed from the process table.
	# This way the pid-polling is same regardless of
	# whether the process is our child or not
	os.wait()

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
	
	raise ServiceNotFound

def start_service(name, command, stdout_fd, stderr_fd):
	pid = os.fork()
	if pid != 0:
		return pid
	
	os.dup2(stdout_fd, 1)
	os.dup2(stderr_fd, 2)
	os.putenv(SERVICE_VAR, name)
	os.setsid()
	os.execvp(command[0], command)

